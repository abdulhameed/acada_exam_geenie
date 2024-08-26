from django.urls import path
from . import views


urlpatterns = [
    path('schools/create/', views.school_create, name='school_create'),
    path('schools/<int:pk>/', views.school_detail, name='school_detail'),
]
