from django.contrib import admin
from .models import Exam, Question, StudentExam, Answer, Result

admin.site.register(Exam)
admin.site.register(Question)
admin.site.register(StudentExam)
admin.site.register(Answer)
admin.site.register(Result)
