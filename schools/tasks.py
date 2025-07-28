from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_invite_email(email, role, invite_url):
    subject = f'Invitation to join as {role}'
    message = f'You have been invited to join as {role}. Click here to accept: {invite_url}'
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
