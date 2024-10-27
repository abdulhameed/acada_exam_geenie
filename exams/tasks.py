from celery import shared_task
from .ai_utils import generate_exam_questions
import logging
# from django.core.management import call_command
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Exam, StudentExam
from django.utils import timezone


logger = logging.getLogger(__name__)


@shared_task
def generate_exam_questions_task(exam_id):
    try:
        result = generate_exam_questions(exam_id)
        logger.info(f"Successfully generated questions for exam {exam_id}")
        return result
    except Exception as e:
        logger.error(f"Error generating questions for exam {exam_id}: {str(e)}")
        raise
    # return generate_exam_questions(exam_id)


# @shared_task
# def run_manage_exams():
#     call_command('manage_exams')


# @shared_task
# def schedule_overall_exam_end(exam_id):
#     exam = Exam.objects.get(id=exam_id)
#     management.call_command('finalize_exam', exam_id=exam_id)


@shared_task
def schedule_exam_start(exam_id):
    exam = Exam.objects.get(id=exam_id)
    student_exams = StudentExam.objects.filter(exam=exam, status='waiting')

    for student_exam in student_exams:
        student_exam.status = 'in_progress'
        student_exam.start_time = timezone.now()
        student_exam.individual_end_time = student_exam.start_time + exam.duration
        student_exam.save()

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "exam_lobby",
        {
            "type": "exam_message",
            "message": f"Exam {exam.title} has started!"
        }
    )
