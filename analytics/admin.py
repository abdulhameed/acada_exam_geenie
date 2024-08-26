from django.contrib import admin
from .models import ExamAnalytics, CourseAnalytics, SchoolAnalytics

admin.site.register(ExamAnalytics)
admin.site.register(CourseAnalytics)
admin.site.register(SchoolAnalytics)
