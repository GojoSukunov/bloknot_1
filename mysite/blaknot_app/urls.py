from django.urls import path,include
from rest_framework import routers
from .views import (UserViewSet,DealDetailViewSet,DealListViewSet,
                    TasksViewSet,NoteViewSet)

router=routers.DefaultRouter()


router.register(r'User',UserViewSet,basename='user')
router.register(r'Tasks',TasksViewSet,basename='tasks')
router.register(r'Note',NoteViewSet,basename='note')


urlpatterns=[
    path('',include(router.urls)),
    path('deal/<int:pk>/',DealDetailViewSet.as_view(),name='deal-detail'),
    path('deals/',DealListViewSet.as_view(),name='deal-list')
]