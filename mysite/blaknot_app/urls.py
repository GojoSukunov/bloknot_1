from django.urls import path,include
from rest_framework import routers
from .views import (UserProfileViewSet,DealDetailViewSet,DealListViewSet,
                    TasksViewSet,NoteViewSet,RegisterView,CustomLoginView,LogoutView)

router=routers.DefaultRouter()


router.register(r'User',UserProfileViewSet,basename='user')
router.register(r'Tasks',TasksViewSet,basename='tasks')
router.register(r'Note',NoteViewSet,basename='note')


urlpatterns=[
    path('',include(router.urls)),
    path('register/',RegisterView.as_view(),name='register'),
    path('login/',CustomLoginView.as_view(),name='login'),
    path('logout/',LogoutView.as_view(),name='logout'),
    path('deal/<int:pk>/',DealDetailViewSet.as_view(),name='deal-detail'),
    path('deals/',DealListViewSet.as_view(),name='deal-list')
]