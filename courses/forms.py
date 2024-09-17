from django import forms
from courses.models import Course, CourseContent


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['school', 'name', 'code', 'lecturer', 'description']


class CourseContentForm(forms.ModelForm):
    class Meta:
        model = CourseContent
        fields = ['title', 'pdf_file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'pdf_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
