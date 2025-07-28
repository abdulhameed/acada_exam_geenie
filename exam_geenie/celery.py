from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings
# from celery.schedules import crontab
# from exams.tasks import schedule_exam_start
# from django.utils import timezone

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'exam_geenie.settings')

app = Celery('exam_geenie')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)  # TODO

from schools.tasks import send_invite_email
app.task(send_invite_email)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# @app.on_after_finalize.connect
# def setup_periodic_tasks(sender, **kwargs):
#     from exams.models import Exam

#     exams = Exam.objects.filter(date__gte=timezone.now())
#     for exam in exams:
#         sender.add_periodic_task(
#             crontab(minute=exam.date.minute, hour=exam.date.hour, day_of_month=exam.date.day, month_of_year=exam.date.month),
#             schedule_exam_start.s(exam.id),
#        )
