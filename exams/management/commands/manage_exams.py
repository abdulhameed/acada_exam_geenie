from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import F
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from exams.models import Exam, StudentExam


class Command(BaseCommand):
    help = 'Manages exam start and end'

    def handle(self, *args, **options):
        now = timezone.now()
        exams_to_start = StudentExam.objects.filter(date__lte=now, status='scheduled')
        exams_to_end = StudentExam.objects.filter(date__lte=now - F('duration'), status='in_progress')

        channel_layer = get_channel_layer()

        for exam in exams_to_start:
            exam.status = 'in_progress'
            exam.save()
            async_to_sync(channel_layer.group_send)(
                f'exam_{exam.id}',
                {'type': 'exam_start'}
            )

        for exam in exams_to_end:
            exam.status = 'completed'
            exam.save()
            async_to_sync(channel_layer.group_send)(
                f'exam_{exam.id}',
                {'type': 'exam_end'}
            )
