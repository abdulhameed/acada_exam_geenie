from django.urls import path
from . import views

urlpatterns = [
    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('<int:course_id>/update/', views.course_update, name='course_update'),
    path('<int:course_id>/content/create/', views.course_content_create, name='course_content_create'),
    path('course-registration/', views.CourseRegistrationView.as_view(), name='course_registration'),
    path('course-assignment/', views.CourseAssignmentView.as_view(), name='course_assignment'),


]
