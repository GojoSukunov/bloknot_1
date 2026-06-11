from rest_framework import viewsets,generics
from .models import User,Goals,Category,Tasks,Note,Habits
from .serializers import (UserSerializer,
                          CategorySerializer, TasksSerializer, HabitsSerializer, NoteSerializer, GoalsListSerializer,
                          GoalsDetailSerializer)
from rest_framework.filters import SearchFilter,OrderingFilter
from .filters import GoalsFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from .permissions import CheckOwner

class UserViewSet(viewsets.ModelViewSet):
    queryset =User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [SearchFilter]
    search_fields=['username']
    permission_classes = [permissions.IsAuthenticated,CheckOwner]

class GoalsListViewSet(generics.ListCreateAPIView):
    queryset =Goals.objects.all()
    serializer_class = GoalsListSerializer
    filter_backends = [SearchFilter,OrderingFilter,DjangoFilterBackend]
    search_fields=['title_goals','status','now_date']
    ordering_fields=['now_date']
    filterset_class = GoalsFilter
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Goals.objects.filter(user=self.request.user)

class GoalsDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    queryset =Goals.objects.all()
    serializer_class = GoalsDetailSerializer
    permission_classes = [permissions.IsAuthenticated,CheckOwner]

    def get_queryset(self):
        return Goals.objects.filter(user=self.request.user)

class HabitsViewSet(viewsets.ModelViewSet):
    queryset =Habits.objects.all()
    serializer_class = HabitsSerializer
    permission_classes = [permissions.IsAuthenticated,CheckOwner]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Habits.objects.filter(user=self.request.user)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset =Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class NoteViewSet(viewsets.ModelViewSet):
    queryset =Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated,CheckOwner]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TasksViewSet(viewsets.ModelViewSet):
    queryset =Tasks.objects.all()
    serializer_class =TasksSerializer
    permission_classes = [permissions.IsAuthenticated,CheckOwner]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

