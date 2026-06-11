from django.urls import path,include
from rest_framework import routers
from .views import (UserViewSet,GoalsDetailViewSet,GoalsListViewSet,
                    CategoryViewSet,HabitsViewSet,TasksViewSet,NoteViewSet)

router=routers.DefaultRouter()


router.register(r'User',UserViewSet,basename='user')
router.register(r'Category',CategoryViewSet,basename='category')
router.register(r'Habits',HabitsViewSet,basename='habits')
router.register(r'Tasks',TasksViewSet,basename='tasks')
router.register(r'Note',NoteViewSet,basename='note')


urlpatterns=[
    path('',include(router.urls)),
    path('goals/<int:pk>/',GoalsDetailViewSet.as_view(),name='goals-detail'),
    path('goals/',GoalsListViewSet.as_view(),name='goals-list')
]