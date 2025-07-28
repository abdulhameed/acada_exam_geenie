from django import forms
from .models import Answer, Exam, Question, StudentExam


# class ExamForm(forms.ModelForm):
#     date = forms.DateTimeField(
#         widget=forms.DateTimeInput(
#             attrs={
#                 'class': 'form-control datetimepicker-input',
#                 'data-target': '#datetimepicker1'
#                 }
#                 )
#     )
#     duration = forms.DurationField(
#         widget=forms.TextInput(attrs={'class': 'form-control timepicker'})
#     )

#     class Meta:
#         model = Exam
#         fields = [
#             'course',
#             'title',
#             'description',
#             'date',
#             'duration',
#             'number_of_questions',
#             'difficulty',
#             'unique_questions'
#             ]
#         widgets = {
#             'course': forms.Select(attrs={'class': 'form-control'}),
#             'title': forms.TextInput(attrs={'class': 'form-control'}),
#             'description': forms.Textarea(attrs={'class': 'form-control'}),
#             'number_of_questions': forms.NumberInput(attrs={
#                 'class': 'form-control'
#                 }
#                 ),
#             'difficulty': forms.Select(attrs={'class': 'form-control'}),
#             'unique_questions': forms.CheckboxInput(attrs={
#                 'class': 'form-check-input'
#                 }
#                 ),
#         }


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
            'mcq_questions',
            'essay_questions',
            'difficulty',
            'unique_questions'
        ]
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'number_of_questions': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'mcq_questions': forms.NumberInput(attrs={
                'class': 'form-control question-count',
                'min': '0'
            }),
            'essay_questions': forms.NumberInput(attrs={
                'class': 'form-control question-count',
                'min': '0'
            }),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'unique_questions': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        number_of_questions = cleaned_data.get('number_of_questions')
        mcq_questions = cleaned_data.get('mcq_questions')
        essay_questions = cleaned_data.get('essay_questions')

        if number_of_questions and mcq_questions is not None and essay_questions is not None:
            if mcq_questions + essay_questions != number_of_questions:
                raise forms.ValidationError(
                    "The sum of MCQ and essay questions must equal the total number of questions."
                )

        return cleaned_data


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
