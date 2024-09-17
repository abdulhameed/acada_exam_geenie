from django import forms
from .models import Answer, Exam, Question, StudentExam


class ExamForm(forms.ModelForm):
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'class': 'form-control datetimepicker-input',
                'data-target': '#datetimepicker1'
                }
                )
    )
    duration = forms.DurationField(
        widget=forms.TextInput(attrs={'class': 'form-control timepicker'})
    )

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
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'number_of_questions': forms.NumberInput(attrs={
                'class': 'form-control'
                }
                ),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'unique_questions': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
                }
                ),
        }


class StudentExamForm(forms.ModelForm):
    class Meta:
        model = StudentExam
        fields = ['student', 'exam', 'start_time', 'end_time', 'status']


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'difficulty']


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['text']
