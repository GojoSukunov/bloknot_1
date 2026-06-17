from rest_framework import viewsets,generics
from .models import User,Deal,Tasks,Note
from .serializers import (UserSerializer,
                         TasksSerializer,  NoteSerializer, DealListSerializer,
                          DealDetailSerializer)
from rest_framework.filters import SearchFilter,OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from .permissions import CheckOwner

class UserViewSet(viewsets.ModelViewSet):
    queryset =User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [SearchFilter]
    search_fields=['username']
    permission_classes = [permissions.IsAuthenticated,CheckOwner]
class DealListViewSet(generics.ListCreateAPIView):
    queryset =Deal.objects.all()
    serializer_class = DealListSerializer
    filter_backends = [SearchFilter,OrderingFilter,DjangoFilterBackend]
    search_fields=['title_deal','status','now_date']
    ordering_fields=['created_at']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
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

