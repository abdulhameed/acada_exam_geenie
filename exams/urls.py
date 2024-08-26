from django.urls import path
from . import views

urlpatterns = [
    path('exams/create/', views.exam_create, name='exam_create'),
    path('exams/<int:pk>/', views.exam_detail, name='exam_detail'),
    path('student-exams/create/', views.student_exam_create, name='student_exam_create'),
    path('student-exams/<int:pk>/', views.student_exam_detail, name='student_exam_detail'),
]