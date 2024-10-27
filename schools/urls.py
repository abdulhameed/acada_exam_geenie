from django.urls import path
from . import views
from users.views import student_signup


urlpatterns = [
    path('school/create/', views.school_create, name='school_create'),
    path('school/<slug:slug>/', views.school_detail, name='school_detail'),
    path('school/<slug:school_slug>/invite/', views.invite_user, name='invite_user'),
    path('invite/accept/<str:token>/', views.accept_invite, name='accept_invite'),
    path('school/<slug:slug>/signup/<str:role>/', student_signup, name='user_signup'),
]
