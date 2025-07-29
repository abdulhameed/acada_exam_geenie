from django.core.management.base import BaseCommand
from django.utils import timezone
from exams.models import Exam, StudentExam


class Command(BaseCommand):
    help = 'Finalizes an exam, completing any remaining active student exams'

    def add_arguments(self, parser):
        parser.add_argument('exam_id', type=int)

    def handle(self, *args, **options):
        exam_id = options['exam_id']
        exam = Exam.objects.get(id=exam_id)
        
        active_student_exams = StudentExam.objects.filter(
            exam=exam,
            status='in_progress'
        )
        
        for student_exam in active_student_exams:
            student_exam.status = 'completed'
            student_exam.individual_end_time = timezone.now()
            student_exam.save()
            
        exam.status = 'completed'
        exam.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully finalized exam {exam_id}'))