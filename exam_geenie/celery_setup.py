from celery.schedules import crontab
from django.utils import timezone
from exam_geenie.celery import app
from exams.tasks import schedule_exam_start
from exams.models import Exam

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    exams = Exam.objects.filter(date__gte=timezone.now())
    for exam in exams:
        sender.add_periodic_task(
            crontab(minute=exam.date.minute, hour=exam.date.hour, day_of_month=exam.date.day, month_of_year=exam.date.month),
            schedule_exam_start.s(exam.id),
        )