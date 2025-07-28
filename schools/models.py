from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string


# Create your models here.
class School(models.Model):
    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    registration_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('school_detail', kwargs={'slug': self.slug})


class SchoolInvite(models.Model):
    ROLES = (
        ('lecturer', 'Lecturer'),
        ('hod', 'Head of Department'),
        ('school_admin', 'School Administrator'),
    )
    school = models.ForeignKey('School', on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLES)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = get_random_string(64)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invite for {self.email} as {self.get_role_display()} at {self.school.name}"
