from django.urls import path
from . import views

urlpatterns = [
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
]
