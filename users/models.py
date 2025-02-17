from django.contrib.auth.models import AbstractUser
from django.db import models
from schools.models import School
from django.utils.crypto import get_random_string


# student, lecturer, hod, school_admin
class CustomUser(AbstractUser):
    ROLES = (
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
        ('hod', 'Head of Department'),
        ('school_admin', 'School Administrator'),
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        null=True,
        blank=True
        )
    role = models.CharField(max_length=20, choices=ROLES)
    department = models.CharField(max_length=100, blank=True)
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    is_school_admin = models.BooleanField(default=False)

    def __str__(self):
        school_name = self.school.name if self.school else 'No school'
        return (
            f"{self.username} ({self.get_role_display()} "
            f"at {school_name})"
        )

    def is_lecturer_for_course(self, course):
        return self == course.lecturer

    def can_create_course_content(self, course):
        return self.is_school_admin or self.is_lecturer_for_course(course)


class RegistrationInvite(models.Model):
    email = models.EmailField()
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = get_random_string(64)
        super().save(*args, **kwargs)
