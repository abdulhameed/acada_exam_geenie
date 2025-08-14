"""
Content processors for handling multiple file formats in ExamGenie
Create this file at: courses/content_processors.py
"""

import os
import json
import csv
import logging
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.conf import settings
import requests
from io import StringIO

# Import libraries for file processing
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Main content processor that routes to specific processors based on file type"""
    
    def __init__(self):
        self.processors = {
            'PDF': self.process_pdf,
            'DOCX': self.process_docx,
            'TXT': self.process_txt,
            'CSV': self.process_csv_expert_questions,
            'JSON': self.process_json_expert_questions,
            'VIDEO': self.process_video_transcript,
            'URL': self.process_url_content,
        }
    
    def process_content(self, content_obj) -> Tuple[bool, str]:
        """
        Process content based on its type
        Returns: (success: bool, message: str)
        """
        try:
            content_obj.processing_status = 'processing'
            content_obj.save()
            
            processor = self.processors.get(content_obj.content_type)
            if not processor:
                error_msg = f"No processor available for {content_obj.content_type}"
                self._update_processing_error(content_obj, error_msg)
                return False, error_msg
            
            # Process the content
            extracted_text, word_count, metadata = processor(content_obj)
            
            # Update the content object
            content_obj.extracted_text = extracted_text
            content_obj.word_count = word_count
            content_obj.is_processed = True
            content_obj.processing_status = 'completed'
            content_obj.last_processed = timezone.now()
            content_obj.processing_error = ''
            content_obj.save()
            
            # Handle any additional metadata (like expert questions)
            if metadata and content_obj.content_type in ['CSV', 'JSON']:
                self._import_expert_questions(content_obj, metadata)
            
            return True, f"Successfully processed {content_obj.content_type} content"
            
        except Exception as e:
            error_msg = f"Error processing {content_obj.content_type}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._update_processing_error(content_obj, error_msg)
            return False, error_msg
    
    def _update_processing_error(self, content_obj, error_msg: str):
        """Update content object with processing error"""
        content_obj.processing_status = 'failed'
        content_obj.processing_error = error_msg
        content_obj.last_processed = timezone.now()
        content_obj.save()
    
    def process_pdf(self, content_obj) -> Tuple[str, int, Dict]:
        """Process PDF files"""
        if not PdfReader:
            raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")
        
        if content_obj.content_file:
            reader = PdfReader(content_obj.content_file.path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        else:
            text = content_obj.text_content
        
        word_count = len(text.split())
        return text, word_count, {}
    
    def process_docx(self, content_obj) -> Tuple[str, int, Dict]:
        """Process Word documents"""
        if not Document:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")
        
        if content_obj.content_file:
            doc = Document(content_obj.content_file.path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        else:
            text = content_obj.text_content
        
        word_count = len(text.split())
        return text, word_count, {}
    
    def process_txt(self, content_obj) -> Tuple[str, int, Dict]:
        """Process plain text files"""
        if content_obj.content_file:
            with open(content_obj.content_file.path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            text = content_obj.text_content
        
        word_count = len(text.split())
        return text, word_count, {}
    
    def process_csv_expert_questions(self, content_obj) -> Tuple[str, int, Dict]:
        """Process CSV files containing expert questions (like LearningQ)"""
        if not pd:
            # Fallback to manual CSV processing
            return self._process_csv_manual(content_obj)
        
        if content_obj.content_file:
            df = pd.read_csv(content_obj.content_file.path)
        else:
            # Handle direct text input as CSV
            csv_data = StringIO(content_obj.text_content)
            df = pd.read_csv(csv_data)
        
        # Convert to list of dictionaries for easier processing
        questions_data = df.to_dict('records')
        
        # Create summary text
        summary = f"Expert Questions Dataset\n"
        summary += f"Total Questions: {len(questions_data)}\n"
        
        if 'question_type' in df.columns:
            type_counts = df['question_type'].value_counts()
            summary += f"Question Types: {dict(type_counts)}\n"
        
        if 'domain' in df.columns:
            domain_counts = df['domain'].value_counts()
            summary += f"Domains: {dict(domain_counts)}\n"
        
        # Sample questions for text content
        sample_questions = questions_data[:5]
        summary += "\nSample Questions:\n"
        for i, q in enumerate(sample_questions, 1):
            question_text = q.get('question_text', 'No question text')[:100]
            summary += f"{i}. {question_text}...\n"
        
        word_count = len(summary.split())
        
        return summary, word_count, {'questions_data': questions_data}
    
    def _process_csv_manual(self, content_obj) -> Tuple[str, int, Dict]:
        """Manual CSV processing without pandas"""
        if content_obj.content_file:
            with open(content_obj.content_file.path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                questions_data = list(reader)
        else:
            csv_data = StringIO(content_obj.text_content)
            reader = csv.DictReader(csv_data)
            questions_data = list(reader)
        
        # Create summary
        summary = f"Expert Questions Dataset\nTotal Questions: {len(questions_data)}\n"
        
        # Sample questions
        sample_questions = questions_data[:5]
        summary += "\nSample Questions:\n"
        for i, q in enumerate(sample_questions, 1):
            question_text = q.get('question_text', 'No question text')[:100]
            summary += f"{i}. {question_text}...\n"
        
        word_count = len(summary.split())
        return summary, word_count, {'questions_data': questions_data}
    
    def process_json_expert_questions(self, content_obj) -> Tuple[str, int, Dict]:
        """Process JSON files containing expert questions"""
        if content_obj.content_file:
            with open(content_obj.content_file.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = json.loads(content_obj.text_content)
        
        # Handle different JSON structures
        if isinstance(data, list):
            questions_data = data
        elif isinstance(data, dict) and 'questions' in data:
            questions_data = data['questions']
        else:
            raise ValueError("JSON must be a list of questions or contain a 'questions' key")
        
        # Create summary
        summary = f"Expert Questions Dataset (JSON)\n"
        summary += f"Total Questions: {len(questions_data)}\n"
        
        # Sample questions
        sample_questions = questions_data[:5]
        summary += "\nSample Questions:\n"
        for i, q in enumerate(sample_questions, 1):
            question_text = q.get('question_text', 'No question text')[:100]
            summary += f"{i}. {question_text}...\n"
        
        word_count = len(summary.split())
        return summary, word_count, {'questions_data': questions_data}
    
    def process_video_transcript(self, content_obj) -> Tuple[str, int, Dict]:
        """Process video transcripts"""
        # For now, treat as text content
        # Could be extended to automatically fetch YouTube transcripts
        text = content_obj.text_content
        if not text and content_obj.content_url:
            # Could implement YouTube transcript extraction here
            text = f"Video URL: {content_obj.content_url}\n(Transcript extraction not implemented)"
        
        word_count = len(text.split())
        return text, word_count, {}
    
    def process_url_content(self, content_obj) -> Tuple[str, int, Dict]:
        """Process web content from URLs"""
        if not content_obj.content_url:
            raise ValueError("URL content type requires a valid URL")
        
        try:
            response = requests.get(content_obj.content_url, timeout=30)
            response.raise_for_status()
            
            # Basic text extraction (could be enhanced with BeautifulSoup)
            text = response.text
            
            # Simple HTML tag removal for basic content extraction
            import re
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            word_count = len(text.split())
            return text, word_count, {}
            
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch URL content: {str(e)}")
    
    def _import_expert_questions(self, content_obj, metadata: Dict):
        """Import expert questions into the database"""
        from .models import ExpertQuestionDataset, ExpertQuestion
        
        questions_data = metadata.get('questions_data', [])
        if not questions_data:
            return
        
        # Create or get dataset
        dataset, created = ExpertQuestionDataset.objects.get_or_create(
            name=f"{content_obj.course.code} - {content_obj.title}",
            defaults={
                'description': f"Expert questions imported from {content_obj.content_type} file",
                'source_type': 'imported'
            }
        )
        
        # Import questions
        imported_count = 0
        for q_data in questions_data:
            question_id = q_data.get('question_id', f"imported_{imported_count}")
            
            # Skip if question already exists
            if ExpertQuestion.objects.filter(question_id=question_id).exists():
                continue
            
            ExpertQuestion.objects.create(
                dataset=dataset,
                question_id=question_id,
                question_text=q_data.get('question_text', ''),
                question_type=q_data.get('question_type', 'MCQ').upper(),
                source_material=q_data.get('source_material', ''),
                domain=q_data.get('domain', ''),
                difficulty_level=self._map_difficulty(q_data.get('difficulty', 'unknown')),
                video_title=q_data.get('video_title', ''),
                video_youtube_link=q_data.get('video_youtube_link', ''),
                video_id=q_data.get('video_id', ''),
                file_source=q_data.get('file_source', ''),
            )
            imported_count += 1
        
        logger.info(f"Imported {imported_count} expert questions from {content_obj.title}")
    
    def _map_difficulty(self, difficulty: str) -> str:
        """Map various difficulty representations to standard levels"""
        difficulty = str(difficulty).lower()
        
        if difficulty in ['easy', 'beginner', 'basic', '1']:
            return 'easy'
        elif difficulty in ['medium', 'intermediate', 'moderate', '2']:
            return 'medium'
        elif difficulty in ['hard', 'difficult', 'advanced', 'expert', '3']:
            return 'hard'
        else:
            return 'unknown'