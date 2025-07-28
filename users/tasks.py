from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings

email_host_user = settings.DEFAULT_FROM_EMAIL


@shared_task
def send_student_registration_email(email, school_name, token, domain):
    # Generate registration URL
    registration_url = reverse('register_with_token', args=[token])
    absolute_url = f'http://{domain}{registration_url}'

    # Render email template
    message = render_to_string('registration/student_invite_email.html', {
        'school_name': school_name,
        'registration_url': absolute_url,
    })

    # Send email
    send_mail(
        f'Complete your registration at {school_name}',
        message,
        from_email=email_host_user,
        recipient_list=[email],
        html_message=message,
        fail_silently=False,
    )
