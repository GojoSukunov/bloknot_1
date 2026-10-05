from rest_framework import viewsets,generics
from .models import User,Deal,Tasks,Note
from .serializers import (RegisterSerializer,
                         TasksSerializer,  NoteSerializer, DealListSerializer,
                          DealDetailSerializer,LoginSerializer,UserProfileSerializer)
from rest_framework.filters import SearchFilter,OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from .permissions import CheckOwner
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CustomLoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({"detail": "Неверные учетные данные"}, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data
        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutView(generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset =User.objects.all()
    serializer_class = UserProfileSerializer
    filter_backends = [SearchFilter]
    search_fields=['username']
    permission_classes = [permissions.IsAuthenticated,CheckOwner]
class DealListViewSet(generics.ListCreateAPIView):
    queryset =Deal.objects.all()
    serializer_class = DealListSerializer
    filter_backends = [SearchFilter,OrderingFilter,DjangoFilterBackend]
    search_fields=['title_deal','status','created_at']
    ordering_fields=['created_at']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return Deal.objects.none()

        return Deal.objects.filter(owner=self.request.user)

class DealDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    queryset =Deal.objects.all()
    serializer_class = DealDetailSerializer
    permission_classes = [permissions.IsAuthenticated,CheckOwner]

    def get_queryset(self):
        return Deal.objects.filter(owner=self.request.user)

class NoteViewSet(viewsets.ModelViewSet):
    queryset =Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated,CheckOwner]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class TasksViewSet(viewsets.ModelViewSet):
    queryset =Tasks.objects.all()
    serializer_class =TasksSerializer
    permission_classes = [permissions.IsAuthenticated,CheckOwner]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

