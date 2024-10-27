from django.conf import settings
from django.db import models
from schools.models import School
from users.models import CustomUser


class Course(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    lecturer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_courses',
        blank=True
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('school', 'code')

    def __str__(self):
        return f"{self.code}: {self.name} ({self.school.name})"


class CourseContent(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='contents'
        )
    title = models.CharField(max_length=200)
    pdf_file = models.FileField(upload_to='course_contents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.code} - {self.title}"
