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
    school = get_object_or_404(School, slug=slug)
    return render(
        request,
        'schools/school_detail.html',
        {'school': school})


@login_required
def invite_user(request, school_slug):
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
    invite = get_object_or_404(SchoolInvite, token=token)

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = invite.email
            user.school = invite.school
            user.role = invite.role
            if invite.role == 'school_admin':
                user.is_school_admin = True
            user.save()
            login(request, user)
            invite.delete()
            return redirect('school_detail', slug=invite.school.slug)
    else:
        form = CustomUserCreationForm(initial={'email': invite.email})

    return render(request, 'users/accept_invite.html', {'form': form, 'invite': invite})


# @login_required
# def invite_school_admin(request, school_slug):
#     school = get_object_or_404(School, slug=school_slug)
#     if not request.user.is_school_admin or request.user.school != school:
#         return HttpResponseForbidden()
    
#     if request.method == 'POST':
#         form = SchoolAdminInviteForm(request.POST)
#         if form.is_valid():
#             invite = form.save(commit=False)
#             invite.school = school
#             invite.save()
            
#             invite_url = request.build_absolute_uri(
#                 reverse('accept_invite', kwargs={'token': invite.token})
#             )
#             send_mail(
#                 'Invitation to be School Admin',
#                 f'You have been invited to be a school admin. Click here to accept: {invite_url}',
#                 'from@example.com',
#                 [invite.email],
#                 fail_silently=False,
#             )
#             return redirect('school_detail', slug=school_slug)
#     else:
#         form = SchoolAdminInviteForm()
    
#     return render(request, 'schools/invite_admin.html', {'form': form, 'school': school})
