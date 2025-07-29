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
from users.forms import CustomLoginForm, CustomUserCreationForm, StudentEmailForm, StudentRegistrationForm
from users.models import CustomUser, RegistrationInvite
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.conf import settings

from users.tasks import send_student_registration_email


email_host_user = settings.EMAIL_HOST_USER

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
    """
    Handles the signup process for students at a specific school.

    Args:
        request (HttpRequest): The HTTP request object.
        slug (str): The slug of the school the student is signing up for.
        role (str): The role of the user (in this case, expected to be 'student').

    Returns:
        HttpResponse: Renders the student signup form for GET requests or invalid POST requests.
        HttpResponseRedirect: Redirects to the school detail page or student dashboard on successful signup.
    """
    # Retrieve the school object using the provided slug or return 404 if not found
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


def request_student_registration(request, school_slug):
    school = get_object_or_404(School, slug=school_slug)

    if request.method == 'POST':
        form = StudentEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Check if user with this email already exists
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'An account with this email already exists.')
                return redirect('login')

            # Create or get registration invite
            invite, created = RegistrationInvite.objects.get_or_create(
                email=email,
                school=school,
                is_used=False,
                defaults={'token': get_random_string(64)}
            )

            if not created:
                # Update token if invite already exists
                invite.token = get_random_string(64)
                invite.save()

            # Generate registration URL
            # current_site = get_current_site(request)
            domain = request.get_host()

            # Send email asynchronously using Celery
            send_student_registration_email.delay(
                email=email,
                school_name=school.name,
                token=invite.token,
                domain=domain
                # domain=current_site.domain
            )

            # registration_url = reverse('register_with_token', args=[invite.token])
            # absolute_url = f'http://{current_site.domain}{registration_url}'

            # # Send email
            # message = render_to_string('registration/student_invite_email.html', {
            #     'school': school,
            #     'registration_url': absolute_url,
            # })

            # send_mail(
            #     f'Complete your registration at {school.name}',
            #     message,
            #     email_host_user,
            #     [email],
            #     html_message=message,
            # )

            messages.success(
                request,
                'Registration link has been sent to your email address.'
            )
            return redirect('school_detail', slug=school_slug)
    else:
        form = StudentEmailForm()

    return render(request, 'registration/request_student_registration.html', {
        'form': form,
        'school': school
    })


def register_with_token(request, token):
    invite = get_object_or_404(RegistrationInvite, token=token, is_used=False)
    school = invite.school

    if request.method == 'POST':
        form = StudentRegistrationForm(invite.school, request.POST)
        if form.is_valid():
            user = form.save()
            invite.is_used = True
            invite.save()
            login(request, user)  # Automatically log in the user
            return redirect('school_detail', slug=school.slug)
    else:
        form = StudentRegistrationForm(invite.school, initial={'email': invite.email})

    return render(request, 'registration/register_with_token.html', {
        'form': form,
        'school': invite.school
    })
