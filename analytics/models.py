
from django.db import models
from exams.models import Exam
from courses.models import Course
from schools.models import School


class ExamAnalytics(models.Model):
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE)
    average_score = models.FloatField()
    median_score = models.FloatField()
    highest_score = models.FloatField()
    lowest_score = models.FloatField()
    participation_rate = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analytics for {self.exam}"


class CourseAnalytics(models.Model):
    course = models.OneToOneField(Course, on_delete=models.CASCADE)
    average_exam_score = models.FloatField()
    student_engagement_rate = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analytics for {self.course}"


class SchoolAnalytics(models.Model):
    school = models.OneToOneField(School, on_delete=models.CASCADE)
    total_students = models.IntegerField()
    total_courses = models.IntegerField()
    average_exam_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analytics for {self.school}"