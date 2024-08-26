from django.db import models


# Create your models here.
class School(models.Model):
    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    registration_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name