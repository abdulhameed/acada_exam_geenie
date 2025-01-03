from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from schools.forms import SchoolInviteForm
from schools.models import School, SchoolInvite
from schools.tasks import send_invite_email
from users.forms import CustomUserCreationForm, SchoolForm
from django.utils.text import slugify
from django.db import transaction
from django.contrib.auth import login
# from django.core.mail import send_mail
from django.urls import reverse


def school_create(request):
    """
    Handles the creation of a new school and its associated school administrator user.
    - If the request is a POST request, processes form data to create a School instance and a related User.
    - If the request is a GET request, renders the school creation form.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: A rendered template for GET or invalid POST requests.
        HttpResponseRedirect: Redirects to the school detail page on successful creation.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the school first
                    school = School.objects.create(
                        name=form.cleaned_data['new_school_name'],
                        domain=form.cleaned_data['new_school_domain'],
                        address=form.cleaned_data['new_school_address'],
                        slug=slugify(form.cleaned_data['new_school_name'])
                    )

                    # Create the user
                    user = form.save(commit=False)
                    user.school = school
                    user.role = 'school_admin'
                    user.is_school_admin = True
                    user.save()

                    login(request, user)
                    return redirect('school_detail', slug=school.slug)
            except Exception as e:
                print(f"Error creating school and user: {e}")
                form.add_error(None, "Error creating school and user. Please try again.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'schools/school_form.html', {'user_form': form})


def school_detail(request, slug):
    """
    Renders the detailed view of a school.
    - Displays a specific template based on the user's authentication status.

    Args:
        request (HttpRequest): The HTTP request object.
        slug (str): The slug of the school to retrieve.

    Returns:
        HttpResponse: A rendered template with the school's details.
    """
    school = get_object_or_404(School, slug=slug)

    if request.user.is_authenticated:
        template_name = 'schools/school_detail.html'
    else:
        template_name = 'schools/anon_school_detail.html'

    return render(
        request,
        template_name,
        {'request': request, 'school': school}
        )


@login_required
def invite_user(request, school_slug):
    """
    Handles the invitation of a user to a school. Only school admins can perform this action.

    Args:
        request (HttpRequest): The HTTP request object.
        school_slug (str): The slug of the school for which the user is being invited.

    Returns:
        HttpResponse: Renders the invitation form on GET or an invalid POST request.
        HttpResponseRedirect: Redirects to the school detail page on successful invitation.
        HttpResponseForbidden: Returns a forbidden response if the user lacks permissions.
    """
    school = get_object_or_404(School, slug=school_slug)
    if not request.user.is_school_admin or request.user.school != school:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = SchoolInviteForm(request.POST, school=school)
        if form.is_valid():
            invite = form.save()

            invite_url = request.build_absolute_uri(
                reverse('accept_invite', kwargs={'token': invite.token})
            )

            # Send email using Celery task
            send_invite_email.delay(invite.email, invite.get_role_display(), invite_url)

            return redirect('school_detail', slug=school_slug)
    else:
        form = SchoolInviteForm(school=school)

    return render(request, 'schools/invite_user.html', {'form': form, 'school': school})


def accept_invite(request, token):
    """
    Handles the acceptance of a school invitation. 
    Allows the invited user to create an account and link it to the associated school and role.

    Args:
        request (HttpRequest): The HTTP request object.
        token (str): The unique token identifying the invitation.

    Returns:
        HttpResponse: Renders the account creation form if the method is GET or POST with errors.
        HttpResponseRedirect: Redirects to the school detail page upon successful account creation.
    """
    # Retrieve the invitation using the provided token, or return a 404 if invalid
    invite = get_object_or_404(SchoolInvite, token=token)

    if request.method == 'POST':    # Handle form submission
        # Initialize the user creation form with submitted POST data
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():     # Validate the form data
            # Create a new user instance without saving it to the database yet
            user = form.save(commit=False)
            # Populate the user fields with invite details
            user.email = invite.email
            user.school = invite.school
            user.role = invite.role
            if invite.role == 'school_admin':
                user.is_school_admin = True     # Grant school admin privileges if applicable
            user.save()
            login(request, user)
            invite.delete()
            return redirect('school_detail', slug=invite.school.slug)
    else:
        form = CustomUserCreationForm(initial={'email': invite.email})

    return render(request, 'users/accept_invite.html', {'form': form, 'invite': invite})
