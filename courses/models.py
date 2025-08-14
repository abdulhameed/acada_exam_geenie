from django.conf import settings
from django.db import models
from schools.models import School
from users.models import CustomUser


class Course(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    lecturer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_courses',
        blank=True
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('school', 'code')

    def __str__(self):
        return f"{self.code}: {self.name} ({self.school.name})"


class CourseContent(models.Model):
    CONTENT_TYPES = [
        ('pdf', 'PDF Document'),
        ('text', 'Text Content'),
        ('transcript', 'Video Transcript'),
    ]
    
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    file_upload = models.FileField(upload_to='course_materials/', null=True, blank=True)
    text_content = models.TextField(null=True, blank=True)  # New field
    source_identifier = models.CharField(max_length=100, null=True, blank=True)  # LearningQ question ID
    research_mode = models.BooleanField(default=False)  # Flag for research questions

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class QuestionTemplate(models.Model):
    """Store sample questions as templates for AI generation"""
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice Question'),
        ('ESSAY', 'Essay Question'),
        ('BOTH', 'Both MCQ and Essay'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('mixed', 'Mixed Difficulty'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='question_templates')
    title = models.CharField(max_length=200, help_text="e.g., 'Midterm 2023 Sample Questions'")
    description = models.TextField(blank=True, help_text="Brief description of the template")
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='BOTH')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='mixed')
    
    # File upload for template questions
    template_file = models.FileField(
        upload_to='question_templates/',
        help_text="Upload PDF, TXT, or DOCX file containing sample questions"
    )
    
    # Optional: Text field for direct input
    template_text = models.TextField(
        blank=True,
        help_text="Or paste sample questions directly here"
    )
    
    is_active = models.BooleanField(default=True, help_text="Use this template for question generation")
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.course.code} - {self.title}"
    
    def get_template_content(self):
        """Extract content from uploaded file or return text content"""
        if self.template_text.strip():
            return self.template_text
        
        if self.template_file:
            try:
                file_path = self.template_file.path
                file_extension = file_path.lower().split('.')[-1]
                
                if file_extension == 'pdf':
                    from PyPDF2 import PdfReader
                    reader = PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                    return text
                
                elif file_extension == 'txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                
                elif file_extension in ['doc', 'docx']:
                    from docx import Document
                    doc = Document(file_path)
                    return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                
            except Exception as e:
                return f"Error reading file: {str(e)}"
        
        return ""
    