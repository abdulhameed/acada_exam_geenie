from django.shortcuts import (
    get_object_or_404,
    render,
    redirect,
    # get_object_or_404
    )
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from schools.models import School
from users.forms import CustomLoginForm, CustomUserCreationForm, StudentRegistrationForm

# Create your views here.


def user_signup(request, slug, role):
    school = get_object_or_404(School, slug=slug)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, school=school, role=role)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('school_detail', slug=school.slug)
    else:
        form = CustomUserCreationForm(school=school, role=role)
    return render(request, 'users/signup.html', {'form': form, 'school': school, 'role': role})


class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'users/login.html'
    success_url = reverse_lazy('home')


def student_signup(request, slug, role):
    school = get_object_or_404(School, slug=slug)

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.school = school
            user.role = 'student'  # Set role as student
            user.save()

            # Log the user in
            login(request, user)

            # Redirect to school detail page or student dashboard
            return redirect('school_detail', slug=school.slug)
    else:
        form = StudentRegistrationForm()

    return render(request, 'registration/student_signup.html', {
        'form': form,
        'school': school,
        'role': role
    })
