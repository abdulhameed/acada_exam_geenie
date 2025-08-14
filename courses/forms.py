from django import forms
from django.core.exceptions import ValidationError
from courses.models import (
    Course, CourseContent, EnhancedCourseContent, 
    QuestionGenerationTemplate, ExpertQuestionDataset
)
import os


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['school', 'name', 'code', 'lecturer', 'description']


class CourseContentForm(forms.ModelForm):
    class Meta:
        model = CourseContent
        fields = ['title', 'content_type', 'file_upload', 'text_content', 'source_identifier', 'research_mode']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'pdf_file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class CourseRegistrationForm(forms.Form):
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['courses'].queryset = Course.objects.filter(school=user.school)


class EnhancedCourseContentForm(forms.ModelForm):
    """Form for uploading multiple file formats"""
    
    class Meta:
        model = EnhancedCourseContent
        fields = [
            'title', 'content_type', 'content_file', 
            'text_content', 'content_url'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive title for this content'
            }),
            'content_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_content_type'
            }),
            'content_file': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'id_content_file'
            }),
            'text_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Or paste your content directly here...',
                'id': 'id_text_content'
            }),
            'content_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/content',
                'id': 'id_content_url'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content_file'].required = False
        self.fields['text_content'].required = False
        self.fields['content_url'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        content_file = cleaned_data.get('content_file')
        text_content = cleaned_data.get('text_content')
        content_url = cleaned_data.get('content_url')
        
        # Validation based on content type
        if content_type == 'URL':
            if not content_url:
                raise ValidationError("URL is required for URL content type.")
        elif content_type in ['PDF', 'DOCX', 'CSV', 'JSON', 'TXT']:
            if not content_file and not text_content:
                raise ValidationError(
                    f"Either upload a {content_type} file or provide text content."
                )
            
            # Validate file extension if file is provided
            if content_file:
                file_extension = os.path.splitext(content_file.name)[1].lower()
                expected_extensions = {
                    'PDF': ['.pdf'],
                    'DOCX': ['.docx', '.doc'],
                    'CSV': ['.csv'],
                    'JSON': ['.json'],
                    'TXT': ['.txt'],
                }
                
                if content_type in expected_extensions:
                    if file_extension not in expected_extensions[content_type]:
                        raise ValidationError(
                            f"File must have extension: {', '.join(expected_extensions[content_type])}"
                        )
        
        return cleaned_data


class QuestionGenerationTemplateForm(forms.ModelForm):
    """Form for configuring question generation templates"""
    
    class Meta:
        model = QuestionGenerationTemplate
        fields = [
            'name', 'description', 'use_expert_questions',
            'expert_question_domains', 'expert_question_types',
            'similarity_threshold', 'max_expert_examples',
            'custom_prompt_prefix', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Template name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of this template'
            }),
            'use_expert_questions': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'expert_question_domains': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Science, Math, Biology (comma-separated)'
            }),
            'expert_question_types': forms.Select(attrs={
                'class': 'form-control'
            }),
            'similarity_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.0',
                'max': '1.0'
            }),
            'max_expert_examples': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10'
            }),
            'custom_prompt_prefix': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional instructions for AI question generation...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ExpertQuestionUploadForm(forms.Form):
    """Form for uploading expert question datasets"""
    
    dataset_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., LearningQ Research Sample'
        }),
        help_text="Name for this expert question dataset"
    )
    
    dataset_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Description of the dataset and its source...'
        }),
        help_text="Optional description"
    )
    
    source_type = forms.ChoiceField(
        choices=[
            ('research', 'Research Dataset'),
            ('custom', 'Custom Expert Questions'),
            ('imported', 'Imported Questions'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='research'
    )
    
    expert_questions_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.json'
        }),
        help_text="Upload CSV or JSON file containing expert questions"
    )
    
    overwrite_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Overwrite questions with duplicate IDs"
    )
    
    def clean_expert_questions_file(self):
        file = self.cleaned_data.get('expert_questions_file')
        if file:
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension not in ['.csv', '.json']:
                raise ValidationError("File must be CSV or JSON format")
        return file


class ContentProcessingForm(forms.Form):
    """Form for processing uploaded content"""
    
    process_all = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Process all pending content",
        help_text="Process all uploaded content that hasn't been processed yet"
    )
    
    force_reprocess = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Force reprocessing",
        help_text="Reprocess content even if it was already processed"
    )
# 