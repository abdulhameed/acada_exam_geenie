import os
import pandas as pd
import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from courses.models import ExpertQuestion, AIGeneratedQuestion
from exams.enhanced_ai_utils import EnhancedQuestionGenerator

class Command(BaseCommand):
    help = 'Manually generate questions in small batches for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='research_source_materials.csv',
            help='CSV file name in project root'
        )
        parser.add_argument(
            '--range',
            type=str,
            required=True,
            help='Range to process (e.g., "1-5", "6-10", "1-50")'
        )
        parser.add_argument(
            '--max-tokens',
            type=int,
            default=800,
            help='Maximum tokens for generation'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without generating'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate even if AI question already exists'
        )
        parser.add_argument(
            '--inspect',
            action='store_true',
            help='Show detailed inspection of each generated question'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        range_str = options['range']
        max_tokens = options['max_tokens']
        dry_run = options['dry_run']
        force = options['force']
        inspect = options['inspect']
        
        # Parse range
        try:
            start, end = map(int, range_str.split('-'))
        except ValueError:
            raise CommandError('Range must be in format "start-end" (e.g., "1-10")')
        
        # Load CSV
        csv_path = os.path.join(settings.BASE_DIR, csv_file)
        if not os.path.exists(csv_path):
            raise CommandError(f'CSV file not found: {csv_path}')
        
        df = pd.read_csv(csv_path)
        
        # Apply range filter
        batch_df = df.iloc[start-1:end]  # Convert to 0-based indexing
        
        if batch_df.empty:
            raise CommandError(f'No questions found in range {range_str}')
        
        self.stdout.write(f'🎯 Processing Range: {range_str} ({len(batch_df)} questions)')
        self.stdout.write(f'🔧 Max Tokens: {max_tokens}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🧪 DRY RUN MODE - No questions will be generated'))
            self.show_batch_preview(batch_df)
            return
        
        # Initialize generator
        generator = EnhancedQuestionGenerator()
        batch_id = f"manual_batch_{range_str.replace('-', '_')}_{timezone.now().strftime('%Y%m%d_%H%M')}"
        
        self.stdout.write(f'🚀 Starting generation...')
        self.stdout.write(f'📦 Batch ID: {batch_id}')
        
        # Process each question
        results = {
            'successful': [],
            'failed': [],
            'skipped': [],
            'errors': []
        }
        
        for idx, row in batch_df.iterrows():
            question_id = row['question_id']
            actual_row_number = idx + 1  # DataFrame index to actual row number
            
            self.stdout.write(f'\n--- Processing {actual_row_number}/{len(df)}: {question_id} ---')
            
            try:
                # Check if already exists
                if not force:
                    existing = AIGeneratedQuestion.objects.filter(
                        original_question_id=question_id
                    ).first()
                    
                    if existing:
                        self.stdout.write(
                            self.style.WARNING(f'⏭️  Skipping - AI question already exists (ID: {existing.id})')
                        )
                        results['skipped'].append(question_id)
                        continue
                
                # Find corresponding expert question
                try:
                    expert_question = ExpertQuestion.objects.get(question_id=question_id)
                except ExpertQuestion.DoesNotExist:
                    error_msg = f"ExpertQuestion not found for ID: {question_id}"
                    self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
                    results['errors'].append({'question_id': question_id, 'error': error_msg})
                    continue
                
                # Generate the question
                self.stdout.write(f'🤖 Generating {row["question_type"]} question...')
                
                start_time = time.time()
                generated_result = self.generate_single_question(
                    generator=generator,
                    source_material=row['source_material'],
                    question_type=row['question_type'],
                    domain=row['domain'],
                    target_question=row['target_question'],
                    max_tokens=max_tokens
                )
                generation_time = time.time() - start_time
                
                if generated_result['success']:
                    # Save to database
                    ai_question = AIGeneratedQuestion.objects.create(
                        original_question_id=question_id,
                        expert_question=expert_question,
                        domain=row['domain'],
                        question_type=row['question_type'],
                        source_material=str(row['source_material'])[:2000],
                        generated_question_text=generated_result['question_text'],
                        reference_question=str(row['target_question']),
                        generation_params={
                            'max_tokens': max_tokens,
                            'model': 'gpt-35-turbo-instruct-0914',
                            'temperature': 0.7,
                            'domain': row['domain'],
                            'expert_question_id': expert_question.id,
                            'batch_id': batch_id
                        },
                        generation_status='completed',
                        quality_score=generated_result.get('confidence_score', 0.8),
                        research_batch=batch_id,
                        processing_duration=generation_time
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f'✅ Success! AI Question ID: {ai_question.id}'))
                    
                    # Show inspection if requested
                    if inspect:
                        self.inspect_generated_question(ai_question, expert_question)
                    
                    results['successful'].append({
                        'question_id': question_id,
                        'ai_id': ai_question.id,
                        'generation_time': generation_time
                    })
                else:
                    error_msg = generated_result.get('error', 'Unknown generation error')
                    self.stdout.write(self.style.ERROR(f'❌ Generation failed: {error_msg}'))
                    results['failed'].append({'question_id': question_id, 'error': error_msg})
            
            except Exception as e:
                error_msg = str(e)
                self.stdout.write(self.style.ERROR(f'❌ Unexpected error: {error_msg}'))
                results['errors'].append({'question_id': question_id, 'error': error_msg})
        
        # Summary
        self.show_batch_summary(results, batch_id)
    
    def generate_single_question(self, generator, source_material, question_type, 
                               domain, target_question, max_tokens):
        """Generate a single question and return result"""
        try:
            # Use your existing generator method
            generated = generator.generate_question_from_source(
                source_material=source_material,
                question_type=question_type,
                domain=domain,
                max_tokens=max_tokens,
                reference_question=target_question
            )
            
            if generated and 'question' in generated:
                return {
                    'success': True,
                    'question_text': generated['question'],
                    'confidence_score': generated.get('confidence_score', 0.8)
                }
            else:
                return {
                    'success': False,
                    'error': 'Generated result was empty or invalid'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def inspect_generated_question(self, ai_question, expert_question):
        """Show detailed inspection of generated vs expert question"""
        self.stdout.write(f'\n🔍 QUESTION INSPECTION:')
        self.stdout.write(f'Expert Question: {expert_question.question_text[:150]}...')
        self.stdout.write(f'AI Generated:    {ai_question.generated_question_text[:150]}...')
        self.stdout.write(f'Quality Score:   {ai_question.quality_score}')
        self.stdout.write(f'Generation Time: {ai_question.processing_duration:.2f}s')
        self.stdout.write(f'Source Length:   {len(ai_question.source_material)} chars')
    
    def show_batch_preview(self, df):
        """Show what would be processed in dry run"""
        self.stdout.write(f'\n📋 Batch Preview:')
        
        for idx, row in df.head(5).iterrows():
            self.stdout.write(f'\n{idx+1}. {row["question_id"]}')
            self.stdout.write(f'   Domain: {row["domain"]}')
            self.stdout.write(f'   Type: {row["question_type"]}')
            self.stdout.write(f'   Source: {str(row["source_material"])[:80]}...')
            self.stdout.write(f'   Target: {str(row["target_question"])[:80]}...')
        
        if len(df) > 5:
            self.stdout.write(f'\n... and {len(df) - 5} more questions')
    
    def show_batch_summary(self, results, batch_id):
        """Show summary of batch processing results"""
        total = len(results['successful']) + len(results['failed']) + len(results['skipped']) + len(results['errors'])
        success_rate = (len(results['successful']) / total * 100) if total > 0 else 0
        
        self.stdout.write(f'\n📊 BATCH SUMMARY ({batch_id}):')
        self.stdout.write(f'✅ Successful: {len(results["successful"])}')
        self.stdout.write(f'❌ Failed: {len(results["failed"])}')
        self.stdout.write(f'⏭️  Skipped: {len(results["skipped"])}')
        self.stdout.write(f'🚫 Errors: {len(results["errors"])}')
        self.stdout.write(f'📈 Success Rate: {success_rate:.1f}%')
        
        if results['successful']:
            avg_time = sum(r['generation_time'] for r in results['successful']) / len(results['successful'])
            self.stdout.write(f'⏱️  Average Generation Time: {avg_time:.2f}s')
        
        # Show recommendations
        self.stdout.write(f'\n💡 Next Steps:')
        
        if success_rate >= 80:
            self.stdout.write('• Success rate is good - you can proceed with larger batches')
            self.stdout.write('• Consider running next batch: increase range size')
        else:
            self.stdout.write('• Review failed questions and fix issues')
            self.stdout.write('• Check source material quality')
            self.stdout.write('• Consider adjusting max_tokens parameter')
        
        if results['failed'] or results['errors']:
            self.stdout.write('• Review error details below:')
            
            # Show failed questions
            for failure in results['failed'][:3]:
                self.stdout.write(f'  Failed: {failure["question_id"]} - {failure["error"]}')
            
            for error in results['errors'][:3]:
                self.stdout.write(f'  Error: {error["question_id"]} - {error["error"]}')

