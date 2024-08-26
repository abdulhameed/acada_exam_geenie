from django.urls import include, path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('signup/', views.user_signup, name='user_signup'),
    # path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('login/', views.CustomLoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
