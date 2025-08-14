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
    
# Add these new models to your existing courses/models.py file

class ExpertQuestionDataset(models.Model):
    """Store expert question datasets like LearningQ"""
    name = models.CharField(max_length=200, help_text="Dataset name (e.g., 'LearningQ Research Sample')")
    description = models.TextField(blank=True)
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('research', 'Research Dataset'),
            ('custom', 'Custom Expert Questions'),
            ('imported', 'Imported Questions'),
        ],
        default='research'
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return self.name


class ExpertQuestion(models.Model):
    """Individual expert questions from research datasets"""
    dataset = models.ForeignKey(ExpertQuestionDataset, on_delete=models.CASCADE, related_name='questions')
    question_id = models.CharField(max_length=200, unique=True)  # Original question ID from dataset
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=[
            ('MCQ', 'Multiple Choice Question'),
            ('ESSAY', 'Essay Question'),
            ('SHORT_ANSWER', 'Short Answer'),
            ('TRUE_FALSE', 'True/False'),
        ]
    )
    source_material = models.TextField(blank=True, help_text="Original educational content")
    domain = models.CharField(max_length=100, blank=True)  # Subject area
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard'),
            ('unknown', 'Unknown'),
        ],
        default='unknown'
    )
    
    # Additional metadata from LearningQ
    video_title = models.CharField(max_length=500, blank=True)
    video_youtube_link = models.URLField(blank=True)
    video_id = models.CharField(max_length=100, blank=True)
    file_source = models.CharField(max_length=200, blank=True)
    
    # Usage tracking
    times_used_as_template = models.IntegerField(default=0)
    quality_rating = models.FloatField(null=True, blank=True, help_text="Expert quality rating (1-5)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['question_id']
        indexes = [
            models.Index(fields=['question_type', 'domain']),
            models.Index(fields=['difficulty_level']),
        ]
    
    def __str__(self):
        return f"{self.question_id}: {self.question_text[:50]}..."


class EnhancedCourseContent(models.Model):
    """Extended course content supporting multiple file formats"""
    CONTENT_TYPES = [
        ('PDF', 'PDF Document'),
        ('DOCX', 'Word Document'),
        ('TXT', 'Text File'),
        ('CSV', 'Expert Questions (CSV)'),
        ('JSON', 'Expert Questions (JSON)'),
        ('VIDEO', 'Video Transcript'),
        ('URL', 'Web Content'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enhanced_contents')
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    
    # File uploads
    content_file = models.FileField(
        upload_to='enhanced_course_contents/',
        null=True, 
        blank=True,
        help_text="Upload PDF, DOCX, TXT, CSV, or JSON file"
    )
    
    # Direct text input
    text_content = models.TextField(blank=True, help_text="Or paste content directly")
    
    # URL for web content
    content_url = models.URLField(blank=True, help_text="URL for web-based content")
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending Processing'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    processing_error = models.TextField(blank=True)
    
    # Extracted content
    extracted_text = models.TextField(blank=True, help_text="Processed text content")
    word_count = models.IntegerField(default=0)
    
    # Metadata
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    last_processed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.course.code} - {self.title} ({self.content_type})"
    
    def process_content(self):
        """Extract and process content based on file type"""
        from .content_processors import ContentProcessor
        processor = ContentProcessor()
        return processor.process_content(self)


class QuestionGenerationTemplate(models.Model):
    """Templates for AI question generation using expert questions"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='generation_templates')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Expert question filters
    use_expert_questions = models.BooleanField(default=True)
    expert_question_domains = models.CharField(
        max_length=500, 
        blank=True, 
        help_text="Comma-separated domains to include (e.g., 'Science,Math')"
    )
    expert_question_types = models.CharField(
        max_length=100,
        choices=[
            ('MCQ', 'MCQ Only'),
            ('ESSAY', 'Essay Only'),
            ('MIXED', 'Mixed Types'),
        ],
        default='MIXED'
    )
    
    # Generation settings
    similarity_threshold = models.FloatField(
        default=0.7, 
        help_text="Minimum similarity to expert questions (0.0-1.0)"
    )
    max_expert_examples = models.IntegerField(
        default=5,
        help_text="Maximum expert questions to use as examples"
    )
    
    # AI prompt customization
    custom_prompt_prefix = models.TextField(
        blank=True,
        help_text="Custom instructions to add to AI prompts"
    )
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.course.code} - {self.name}"