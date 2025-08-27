"""
Django management command to import expert questions from CSV/JSON files
Create this file at: courses/management/commands/import_expert_questions.py

First create these directories if they don't exist:
- courses/management/
- courses/management/commands/

Also create empty __init__.py files in both directories:
- courses/management/__init__.py
- courses/management/commands/__init__.py
"""

import os
import csv
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from courses.models import ExpertQuestionDataset, ExpertQuestion

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import expert questions from CSV or JSON files (like LearningQ dataset)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the CSV or JSON file containing expert questions'
        )
        parser.add_argument(
            '--dataset-name',
            type=str,
            default='Imported Expert Questions',
            help='Name for the expert question dataset'
        )
        parser.add_argument(
            '--dataset-description',
            type=str,
            default='Expert questions imported from external dataset',
            help='Description for the expert question dataset'
        )
        parser.add_argument(
            '--source-type',
            type=str,
            choices=['research', 'custom', 'imported'],
            default='imported',
            help='Type of the source dataset'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing questions with the same ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
    
    def handle(self, *args, **options):
        file_path = options['file_path']
        
        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")
        
        # Determine file type
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.csv':
            questions_data = self.load_csv_data(file_path)
        elif file_extension == '.json':
            questions_data = self.load_json_data(file_path)
        else:
            raise CommandError(f"Unsupported file type: {file_extension}. Use .csv or .json files.")
        
        self.stdout.write(f"Loaded {len(questions_data)} questions from {file_path}")
        
        if options['dry_run']:
            self.preview_import(questions_data)
            return
        
        # Import the data
        with transaction.atomic():
            dataset = self.create_or_get_dataset(
                name=options['dataset_name'],
                description=options['dataset_description'],
                source_type=options['source_type']
            )
            
            imported_count, skipped_count, error_count = self.import_questions(
                dataset, 
                questions_data, 
                overwrite=options['overwrite']
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed:\n"
                f"  - Imported: {imported_count} questions\n"
                f"  - Skipped: {skipped_count} questions\n"
                f"  - Errors: {error_count} questions\n"
                f"  - Dataset: {dataset.name} (ID: {dataset.id})"
            )
        )
    
    def load_csv_data(self, file_path):
        """Load data from CSV file"""
        questions_data = []
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                questions_data.append(row)
        
        return questions_data
    
    def load_json_data(self, file_path):
        """Load data from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
        
        # Handle different JSON structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'questions' in data:
            return data['questions']
        else:
            raise CommandError("JSON must be a list of questions or contain a 'questions' key")
    
    def preview_import(self, questions_data):
        """Preview what would be imported"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("DRY RUN - Preview of import")
        self.stdout.write("="*50)
        
        # Analyze the data
        question_types = {}
        domains = {}
        difficulties = {}
        
        for q in questions_data[:10]:  # Show first 10 questions
            q_type = q.get('question_type', 'Unknown')
            domain = q.get('domain', 'Unknown')
            difficulty = q.get('difficulty', 'Unknown')
            
            question_types[q_type] = question_types.get(q_type, 0) + 1
            domains[domain] = domains.get(domain, 0) + 1
            difficulties[difficulty] = difficulties.get(difficulty, 0) + 1
            
            # Show sample question
            question_text = q.get('question_text', 'No question text')[:100]
            self.stdout.write(f"\nQuestion: {question_text}...")
            self.stdout.write(f"  Type: {q_type}")
            self.stdout.write(f"  Domain: {domain}")
            self.stdout.write(f"  ID: {q.get('question_id', 'No ID')}")
        
        self.stdout.write("\n" + "-"*30)
        self.stdout.write("Summary Statistics:")
        self.stdout.write(f"Total questions: {len(questions_data)}")
        self.stdout.write(f"Question types: {dict(question_types)}")
        self.stdout.write(f"Domains: {dict(domains)}")
        self.stdout.write(f"Difficulties: {dict(difficulties)}")
        self.stdout.write("\nUse --dry-run=False to perform actual import")
    
    def create_or_get_dataset(self, name, description, source_type):
        """Create or get existing dataset"""
        dataset, created = ExpertQuestionDataset.objects.get_or_create(
            name=name,
            defaults={
                'description': description,
                'source_type': source_type,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(f"Created new dataset: {name}")
        else:
            self.stdout.write(f"Using existing dataset: {name}")
        
        return dataset
    
    def import_questions(self, dataset, questions_data, overwrite=False):
        """Import questions into the database - UPDATED for LearningQ data"""
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        for q_data in questions_data:
            try:
                question_id = q_data.get('question_id')
                if not question_id:
                    question_id = f"imported_{imported_count}_{skipped_count}_{error_count}"
                
                # Check if question already exists
                existing_question = ExpertQuestion.objects.filter(question_id=question_id).first()
                
                if existing_question and not overwrite:
                    skipped_count += 1
                    continue
                
                # Handle article_id for Khan Academy articles
                video_id_value = q_data.get('video_id', '') or q_data.get('article_id', '')
                
                # Map and validate data
                question_data = {
                    'dataset': dataset,
                    'question_id': question_id,
                    'question_text': q_data.get('question_text', ''),
                    'question_type': self.map_question_type(q_data.get('question_type', 'MCQ')),
                    'source_material': q_data.get('source_material', ''),
                    'domain': q_data.get('domain', ''),
                    'difficulty_level': self.map_difficulty(q_data.get('difficulty', 'unknown')),
                    'video_title': q_data.get('video_title', ''),
                    'video_youtube_link': q_data.get('video_youtube_link', ''),
                    'video_id': video_id_value,  # Maps both video_id and article_id
                    'file_source': q_data.get('file_source', ''),
                    'quality_rating': self.parse_float(q_data.get('quality_rating')),
                    'is_missing_source': len(q_data.get('source_material', '')) < 100,  # Mark if insufficient source
                }
                
                if existing_question and overwrite:
                    # Update existing question
                    for key, value in question_data.items():
                        if key != 'dataset':  # Don't update dataset
                            setattr(existing_question, key, value)
                    existing_question.save()
                else:
                    # Create new question
                    ExpertQuestion.objects.create(**question_data)
                
                imported_count += 1
                
                if imported_count % 100 == 0:
                    self.stdout.write(f"Imported {imported_count} questions...")
                
            except Exception as e:
                logger.error(f"Error importing question {q_data.get('question_id', 'unknown')}: {str(e)}")
                error_count += 1
                continue
        
        return imported_count, skipped_count, error_count
    
    def map_question_type(self, question_type):
        """Map question type to valid choices - UPDATED for LearningQ data"""
        if not question_type:
            return 'MCQ'
        
        question_type = str(question_type).upper()
        valid_types = ['MCQ', 'ESSAY', 'SHORT_ANSWER', 'TRUE_FALSE']
        
        if question_type in valid_types:
            return question_type
        elif question_type in ['MULTIPLE_CHOICE', 'MC', 'MULTIPLE-CHOICES']:  # Added MULTIPLE-CHOICES
            return 'MCQ'
        elif question_type in ['SHORT', 'SA', 'OPEN-ENDED', 'OPEN_ENDED']:  # Added OPEN-ENDED
            return 'SHORT_ANSWER'
        elif question_type in ['TF', 'T_F', 'TRUE_FALSE']:
            return 'TRUE_FALSE'
        else:
            return 'MCQ'  # Default
    
    def map_difficulty(self, difficulty):
        """Map difficulty to valid choices"""
        if not difficulty:
            return 'unknown'
        
        difficulty = str(difficulty).lower()
        
        if difficulty in ['easy', 'beginner', 'basic', '1']:
            return 'easy'
        elif difficulty in ['medium', 'intermediate', 'moderate', '2']:
            return 'medium'
        elif difficulty in ['hard', 'difficult', 'advanced', 'expert', '3']:
            return 'hard'
        else:
            return 'unknown'
    
    def parse_float(self, value):
        """Safely parse float value"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
