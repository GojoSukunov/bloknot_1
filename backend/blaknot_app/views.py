import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import connection
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import Deal, Note, Tasks
from .permissions import CheckOwner
from .serializers import (ChangePasswordSerializer, DealSerializer, LoginSerializer, NoteSerializer,
                          RegisterSerializer, TasksSerializer, UserProfileSerializer)

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = {"detail": "Неверный логин или пароль."}


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("Зарегистрирован пользователь id=%s", user.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(INVALID_CREDENTIALS, status=status.HTTP_401_UNAUTHORIZED)
        try:
            # django-axes требует настоящий HttpRequest
            user = authenticate(request=request._request, **serializer.validated_data)
        except DjangoPermissionDenied:  # axes: слишком много неудачных попыток
            return Response({"detail": "Слишком много попыток входа. Попробуйте позже."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        if user is None or not user.is_active:
            return Response(INVALID_CREDENTIALS, status=status.HTTP_401_UNAUTHORIZED)

        update_last_login(None, user)
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": {"id": user.pk, "username": user.username, "email": user.email},
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


class RefreshView(TokenRefreshView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "refresh"


class LogoutView(APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data["refresh"])
            if str(token.get("user_id")) != str(request.user.pk):
                return Response(status=status.HTTP_400_BAD_REQUEST)
            token.blacklist()
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """Профиль текущего пользователя (чужие профили недоступны)."""
    serializer_class = UserProfileSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    throttle_scope = "password"

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        # Отзываем все выданные refresh-токены: войти заново нужно на всех устройствах
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)
        return Response({"detail": "Пароль изменён. Войдите заново."})


class DealListCreateView(generics.ListCreateAPIView):
    serializer_class = DealSerializer
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["title_deal", "description"]
    ordering_fields = ["created_at", "updated_at", "cash"]
    filterset_fields = ["status"]

    def get_queryset(self):
        return (Deal.objects.filter(owner=self.request.user)
                .select_related("owner").prefetch_related("note"))

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DealDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DealSerializer
    permission_classes = [permissions.IsAuthenticated, CheckOwner]

    def get_queryset(self):
        return (Deal.objects.filter(owner=self.request.user)
                .select_related("owner").prefetch_related("note"))


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated, CheckOwner]
    filterset_fields = ["deal"]

    def get_queryset(self):
        return Note.objects.filter(deal__owner=self.request.user)


class TasksViewSet(viewsets.ModelViewSet):
    serializer_class = TasksSerializer
    permission_classes = [permissions.IsAuthenticated, CheckOwner]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ["title_task", "description"]
    filterset_fields = ["deal", "status", "level"]

    def get_queryset(self):
        return Tasks.objects.filter(owner=self.request.user).select_related("deal")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


def healthz(request):
    """Проверка живости для мониторинга/оркестратора: отвечает 200, только если БД доступна."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        logger.exception("healthcheck: БД недоступна")
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})
