from django.conf import settings
from django.db import models
from django.utils import timezone
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
    
    # created_at = models.DateTimeField(auto_now_add=True)

    is_missing_source = models.BooleanField(
        default=False, 
        help_text='Indicates if this question is missing source material'
    )
    source_recovery_attempted = models.BooleanField(
        default=False, 
        help_text='Indicates if source recovery has been attempted for this question'
    )
    source_recovery_date = models.DateTimeField(
        blank=True, 
        null=True, 
        help_text='When source material was last recovered or attempted'
    )

    # RESEARCH SELECTION FIELDS 
    is_selected_for_research = models.BooleanField(
        default=False, 
        help_text='Indicates if this question is selected for research comparison'
    )
    selection_date = models.DateTimeField(
        blank=True, 
        null=True, 
        help_text='When this question was selected for research'
    )
    selection_batch = models.CharField(
        max_length=100, 
        blank=True, 
        help_text='Batch identifier for selection (e.g., research_baseline_v1)'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Auto-update is_missing_source flag when saving"""
        self.is_missing_source = not bool(self.source_material and self.source_material.strip())
        super().save(*args, **kwargs)
    
    @property
    def source_status(self):
        """Return human-readable source status"""
        if self.source_material and self.source_material.strip():
            return "✅ Has Source"
        elif self.source_recovery_attempted:
            return "❌ Recovery Failed"
        else:
            return "⚠️ Missing Source"
        
    @property
    def is_research_selected(self):
        """Check if question is selected for research"""
        return self.is_selected_for_research
    
    @property
    def has_adequate_source(self):
        """Check if question has adequate source material for research"""
        return bool(self.source_material and len(self.source_material.strip()) >= 100)
    
    def mark_source_recovery_attempted(self):
        """Mark that source recovery was attempted"""
        self.source_recovery_attempted = True
        self.source_recovery_date = timezone.now()
        self.save()
    
    class Meta:
        # ... your existing meta options ...
        ordering = ['question_id']
        indexes = [
            models.Index(fields=['question_type', 'domain']),
            models.Index(fields=['difficulty_level']),
            # models.Index(fields=['is_missing_source']),
            models.Index(fields=['is_selected_for_research']),
            models.Index(fields=['selection_batch']),
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


# class AIGeneratedQuestion(models.Model):
#     corresponding_expert_question = models.OneToOneField(ExpertQuestion, on_delete=models.CASCADE)
#     question_text = models.TextField()
#     generation_model = models.CharField(max_length=100)  # e.g., "gpt-35-turbo-instruct-0914"
#     generation_parameters = models.JSONField()  # Store temperature, etc.
#     generated_at = models.DateTimeField(auto_now_add=True)
    
#     # Evaluation fields (for later)
#     is_selected_for_evaluation = models.BooleanField(default=True)
    


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
    

class AIGeneratedQuestion(models.Model):
    """
    Model to store AI-generated questions for research comparison
    """
    # Original source tracking
    original_question_id = models.CharField(
        max_length=200, 
        help_text="ID from research_source_materials.csv - maps to ExpertQuestion.question_id"
    )
    expert_question = models.ForeignKey(
        'ExpertQuestion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Direct reference to the original ExpertQuestion model"
    )
    domain = models.CharField(max_length=100, help_text="Subject domain")
    question_type = models.CharField(
        max_length=20,
        choices=[
            ('MCQ', 'Multiple Choice Question'),
            ('ESSAY', 'Essay Question'),
            ('SHORT_ANSWER', 'Short Answer'),
            ('TRUE_FALSE', 'True/False'),
        ]
    )
    
    # Source and generation data
    source_material = models.TextField(help_text="Original educational content")
    reference_question = models.TextField(
        help_text="Target question from CSV for style reference"
    )
    generated_question_text = models.TextField(help_text="AI-generated question")
    
    # Generation metadata
    generation_params = models.JSONField(
        default=dict,
        help_text="Parameters used for generation (model, tokens, temperature, etc.)"
    )
    generation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    generation_timestamp = models.DateTimeField(auto_now_add=True)
    processing_duration = models.FloatField(
        null=True, blank=True,
        help_text="Time taken to generate in seconds"
    )
    
    # Quality and evaluation
    quality_score = models.FloatField(
        null=True, blank=True,
        help_text="AI confidence score (0-1)"
    )
    expert_rating = models.FloatField(
        null=True, blank=True,
        help_text="Expert evaluation score (1-5)"
    )
    educational_value_score = models.IntegerField(
        null=True, blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="Expert rating for educational value"
    )
    clarity_score = models.IntegerField(
        null=True, blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="Expert rating for clarity"
    )
    difficulty_appropriateness = models.IntegerField(
        null=True, blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="Expert rating for difficulty appropriateness"
    )
    blooms_taxonomy_level = models.CharField(
        max_length=20,
        choices=[
            ('remember', 'Remember'),
            ('understand', 'Understand'),
            ('apply', 'Apply'),
            ('analyze', 'Analyze'),
            ('evaluate', 'Evaluate'),
            ('create', 'Create'),
        ],
        blank=True,
        help_text="Cognitive level as rated by expert"
    )
    
    # Research tracking
    is_selected_for_research = models.BooleanField(
        default=True,
        help_text="Whether this question is part of research dataset"
    )
    research_batch = models.CharField(
        max_length=100,
        blank=True,
        help_text="Research batch identifier"
    )
    
    # Automatic metrics (to be calculated)
    bleu_score = models.FloatField(null=True, blank=True)
    meteor_score = models.FloatField(null=True, blank=True)
    rouge_score = models.FloatField(null=True, blank=True)
    question_length = models.IntegerField(null=True, blank=True)
    vocabulary_diversity = models.FloatField(null=True, blank=True)
    syntactic_complexity = models.FloatField(null=True, blank=True)
    
    # Additional metadata
    model_used = models.CharField(
        max_length=100,
        default='gpt-35-turbo-instruct-0914',
        help_text="AI model used for generation"
    )
    prompt_template = models.TextField(
        blank=True,
        help_text="Template used for generation prompt"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if generation failed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses_ai_generated_question'
        indexes = [
            models.Index(fields=['original_question_id']),
            models.Index(fields=['domain']),
            models.Index(fields=['question_type']),
            models.Index(fields=['generation_status']),
            models.Index(fields=['is_selected_for_research']),
            models.Index(fields=['research_batch']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI-Generated Q: {self.original_question_id} ({self.question_type})"
    
    @property
    def generation_success_rate(self):
        """Calculate success rate for this batch"""
        if not self.research_batch:
            return None
        
        batch_questions = AIGeneratedQuestion.objects.filter(research_batch=self.research_batch)
        total = batch_questions.count()
        successful = batch_questions.filter(generation_status='completed').count()
        
        return (successful / total * 100) if total > 0 else 0
    
    def get_truncated_question(self, max_length=100):
        """Get truncated version of generated question for display"""
        if len(self.generated_question_text) <= max_length:
            return self.generated_question_text
        return self.generated_question_text[:max_length] + "..."
    
    def get_truncated_source(self, max_length=200):
        """Get truncated version of source material for display"""
        if len(self.source_material) <= max_length:
            return self.source_material
        return self.source_material[:max_length] + "..."