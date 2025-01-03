from django.db import models
from django.db.models import Count
from courses.models import Course
from users.models import CustomUser
from django.core.exceptions import ValidationError


class Exam(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    duration = models.DurationField()
    # total_questions = models.IntegerField()
    number_of_questions = models.IntegerField()
    mcq_questions = models.IntegerField(default=0, help_text="Number of MCQ questions")
    essay_questions = models.IntegerField(default=0, help_text="Number of essay questions")
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    unique_questions = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Validate that total questions matches sum of question types
        if self.number_of_questions != (self.mcq_questions + self.essay_questions):
            raise ValidationError({
                'number_of_questions': 'Total questions must equal sum of MCQ and essay questions'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_questions_status(self):
        """Returns the status of questions creation progress"""
        question_counts = self.questions.filter(parent__isnull=True).aggregate(
            mcq_count=Count('id', filter=models.Q(question_type='MCQ')),
            essay_count=Count('id', filter=models.Q(question_type='ESSAY'))
        )

        return {
            'mcq': {
                'required': self.mcq_questions,
                'created': question_counts['mcq_count'],
                'remaining': self.mcq_questions - question_counts['mcq_count']
            },
            'essay': {
                'required': self.essay_questions,
                'created': question_counts['essay_count'],
                'remaining': self.essay_questions - question_counts['essay_count']
            }
        }

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice Question'),
        ('ESSAY', 'Essay Question'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_questions')
    order = models.CharField(max_length=20)  # To store "1", "1b", "1b(ix)", etc.
    question_type = models.CharField(max_length=5, choices=QUESTION_TYPES)
    text = models.TextField()
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    difficulty = models.CharField(max_length=20, choices=Exam.DIFFICULTY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        constraints = [
            models.CheckConstraint(
                check=models.Q(question_type__in=['MCQ', 'ESSAY']),
                name='valid_question_type'
            )
        ]

    def clean(self):
        if self.parent:
            if self.question_type != self.parent.question_type:
                raise ValidationError({
                    'question_type': 'Sub-questions must be of the same type as their parent'
                })

        # Validate against exam requirements
        if not self.parent:  # Only check top-level questions
            question_counts = self.exam.get_questions_status()
            if self.question_type == 'MCQ' and question_counts['mcq']['created'] >= self.exam.mcq_questions:
                raise ValidationError('Maximum number of MCQ questions reached')
            elif self.question_type == 'ESSAY' and question_counts['essay']['created'] >= self.exam.essay_questions:
                raise ValidationError('Maximum number of essay questions reached')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_full_order(self):
        if self.parent:
            return f"{self.parent.get_full_order()}.{self.order}"
        return self.order

    def __str__(self):
        return f"Question {self.order} ({self.question_type}) for {self.exam}"


class MCQOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.CharField(max_length=5)  # For options like a), b), c)

    class Meta:
        ordering = ['order']

    def clean(self):
        # Validate that the question is MCQ type
        if self.question.question_type != 'MCQ':
            raise ValidationError('Options can only be added to MCQ questions')

        # Ensure at least one option is marked as correct
        if self.is_correct and not self.pk:  # New correct option
            existing_correct = MCQOption.objects.filter(
                question=self.question,
                is_correct=True
            ).exists()
            if existing_correct:
                raise ValidationError('Only one correct option is allowed per question')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Option {self.order} for {self.question}"


class StudentExam(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    individual_start_time = models.DateTimeField(null=True, blank=True)
    individual_end_time = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    selected_questions = models.ManyToManyField('Question', blank=True, related_name='student_exams')

    def __str__(self):
        return f"{self.student.username} - {self.exam}"

    class Meta:
        unique_together = ['student', 'exam']


class Answer(models.Model):
    student_exam = models.ForeignKey(
        StudentExam,
        on_delete=models.CASCADE,
        related_name='answers'
        )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.TextField()
    grade = models.FloatField(null=True, blank=True)
    ai_feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Answer for {self.question}"
            f" by {self.student_exam.student.username}"
            )


class Result(models.Model):
    student_exam = models.OneToOneField(StudentExam, on_delete=models.CASCADE)
    total_grade = models.FloatField()
    STATUS_CHOICES = [
        ('pending_review', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('sent', 'Sent'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Result for {self.student_exam}"
