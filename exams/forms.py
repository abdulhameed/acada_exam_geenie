from django import forms
from .models import Exam, StudentExam


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            'course',
            'title',
            'description',
            'date',
            'duration',
            'number_of_questions',
            'difficulty',
            'unique_questions'
            ]


class StudentExamForm(forms.ModelForm):
    class Meta:
        model = StudentExam
        fields = ['student', 'exam', 'start_time', 'end_time', 'status']
