from django.db import models
from courses.models import Course
from users.models import CustomUser


class Exam(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    duration = models.DurationField()
    number_of_questions = models.IntegerField()
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ]
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    unique_questions = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class Question(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    text = models.TextField()
    difficulty = models.CharField(
        max_length=20,
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')]
        )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question {self.id} for {self.exam}"
    

class StudentExam(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.student.username} - {self.exam}"


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
