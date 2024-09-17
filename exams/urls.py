from django.urls import path
from . import views

urlpatterns = [
    path('exams/create/', views.exam_create, name='exam_create'),
    path('exams/<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('student-exams/create/', views.student_exam_create, name='student_exam_create'),
    path('student-exams/<int:pk>/', views.student_exam_detail, name='student_exam_detail'),


    path('exams', views.exam_list, name='exam_list'),
    # path('exams/<int:exam_id>/', views.exam_detail, name='exam_detail'),
    # path('create/', views.exam_create, name='exam_create'),
    path('exams/<int:exam_id>/question/create/', views.question_create, name='question_create'),
    path('exams/<int:exam_id>/start/', views.start_exam, name='start_exam'),
    path('exams/take/<int:student_exam_id>/', views.take_exam, name='take_exam'),
    path('exams/results/<int:student_exam_id>/', views.exam_results, name='exam_results'),
]
