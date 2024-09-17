from celery import shared_task
from .ai_utils import generate_exam_questions
import logging


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


@shared_task
def add(x, y):
    return x + y