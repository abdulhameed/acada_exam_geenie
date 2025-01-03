from django.contrib import admin
from .models import Exam, MCQOption, Question, StudentExam, Answer, Result


class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 0


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('exam', 'order', 'question_type', 'marks')
    list_filter = ('exam', 'question_type')
    search_fields = ('text', 'order')
    inlines = [MCQOptionInline]


admin.site.register(Exam)
admin.site.register(Question, QuestionAdmin)
admin.site.register(StudentExam)
admin.site.register(Answer)
admin.site.register(Result)
