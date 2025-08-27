import os
import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from celery import group, chord
from courses.tasks import generate_questions_from_csv_batch, check_batch_progress

class Command(BaseCommand):
    help = 'Generate questions in batch from research_source_materials.csv using Celery'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='research_source_materials.csv',
            help='CSV file name in project root (default: research_source_materials.csv)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of questions to process in parallel per batch (default: 10)'
        )
        parser.add_argument(
            '--max-workers',
            type=int,
            default=5,
            help='Maximum number of parallel workers (default: 5)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without actually generating questions'
        )
        parser.add_argument(
            '--monitor',
            action='store_true',
            help='Monitor the progress of batch processing'
        )
        parser.add_argument(
            '--task-id',
            type=str,
            help='Task ID to monitor (use with --monitor)'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        batch_size = options['batch_size']
        max_workers = options['max_workers']
        dry_run = options['dry_run']
        monitor = options['monitor']
        task_id = options['task_id']

        if monitor:
            if not task_id:
                self.stdout.write(
                    self.style.ERROR('--task-id is required when using --monitor')
                )
                return
            self.monitor_task(task_id)
            return

        # Validate CSV file exists
        csv_path = os.path.join(settings.BASE_DIR, csv_file)
        if not os.path.exists(csv_path):
            raise CommandError(f'CSV file not found: {csv_path}')

        self.stdout.write(
            self.style.SUCCESS(f'🚀 Starting batch question generation...')
        )
        self.stdout.write(f'📄 CSV File: {csv_file}')
        self.stdout.write(f'📦 Batch Size: {batch_size}')
        self.stdout.write(f'⚡ Max Workers: {max_workers}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 DRY RUN MODE - No questions will be generated')
            )
            # Just validate the CSV structure
            self.validate_csv(csv_path)
            return

        try:
            # Start the batch processing task
            task = generate_questions_from_csv_batch.delay(
                csv_filename=csv_file,
                batch_size=batch_size,
                max_workers=max_workers
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Batch processing started!')
            )
            self.stdout.write(f'🔍 Task ID: {task.id}')
            self.stdout.write(
                self.style.WARNING(
                    f'📊 Monitor progress with: python manage.py generate_questions_batch --monitor --task-id {task.id}'
                )
            )
            
        except Exception as e:
            raise CommandError(f'Failed to start batch processing: {str(e)}')

    def validate_csv(self, csv_path):
        """Validate CSV file structure"""
        import pandas as pd
        
        try:
            df = pd.read_csv(csv_path)
            self.stdout.write(f'📊 Loaded {len(df)} rows from CSV')
            
            # Check required columns
            required_columns = ['question_id', 'domain', 'question_type', 'source_material', 'target_question']
            missing_columns = set(required_columns) - set(df.columns)
            
            if missing_columns:
                raise CommandError(f'Missing required columns: {missing_columns}')
            
            # Check for empty values
            for col in required_columns:
                empty_count = df[col].isna().sum()
                if empty_count > 0:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Column "{col}" has {empty_count} empty values')
                    )
            
            # Show sample data
            self.stdout.write('📝 Sample data:')
            for i, row in df.head(3).iterrows():
                self.stdout.write(f'  ID: {row["question_id"]}')
                self.stdout.write(f'  Domain: {row["domain"]}')
                self.stdout.write(f'  Type: {row["question_type"]}')
                self.stdout.write(f'  Source: {str(row["source_material"])[:100]}...')
                self.stdout.write('  ---')
            
            self.stdout.write(
                self.style.SUCCESS('✅ CSV validation passed!')
            )
            
        except Exception as e:
            raise CommandError(f'CSV validation failed: {str(e)}')

    def monitor_task(self, task_id):
        """Monitor task progress"""
        self.stdout.write(f'🔍 Monitoring task: {task_id}')
        self.stdout.write('Press Ctrl+C to stop monitoring\n')
        
        try:
            while True:
                progress = check_batch_progress(task_id)
                
                status = progress.get('status', 'UNKNOWN')
                result = progress.get('result')
                
                self.stdout.write(f'Status: {status}')
                
                if status == 'SUCCESS' and result:
                    self.stdout.write(
                        self.style.SUCCESS('✅ Batch processing completed!')
                    )
                    self.stdout.write(f'📊 Results: {result}')
                    break
                elif status == 'FAILURE':
                    self.stdout.write(
                        self.style.ERROR(f'❌ Task failed: {result}')
                    )
                    break
                elif status == 'PENDING':
                    self.stdout.write('⏳ Task is pending...')
                elif status == 'STARTED':
                    self.stdout.write('🚀 Task has started...')
                
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            self.stdout.write('\n👋 Monitoring stopped.')

