# Save as: courses/management/commands/conservative_recovery.py
# A more conservative approach focusing on high-success methods

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from courses.models import ExpertQuestion, ExpertQuestionDataset
import pandas as pd
import time
import logging
from typing import Optional

class Command(BaseCommand):
    help = 'Conservative source material recovery focusing on high-success methods'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing expert questions'
        )
        parser.add_argument(
            '--dataset-name',
            type=str,
            default='LearningQ Research Sample',
            help='Name of the expert question dataset'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making actual changes to the database'
        )
        parser.add_argument(
            '--videos-only',
            action='store_true',
            help='Only attempt video recovery (skip problematic articles)'
        )
        parser.add_argument(
            '--ultra-slow',
            action='store_true',
            help='Use maximum delays to ensure success'
        )

    def handle(self, *args, **options):
        self.csv_file = options['csv_file']
        self.dataset_name = options['dataset_name']
        self.dry_run = options['dry_run']
        self.videos_only = options['videos_only']
        self.ultra_slow = options['ultra_slow']
        
        # Ultra-conservative settings
        self.video_delay = 5.0 if self.ultra_slow else 3.0
        self.max_retries = 2  # Fewer retries to avoid hitting limits
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize counters
        self.recovered_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 CONSERVATIVE DRY RUN - No database changes')
            )
        
        if self.videos_only:
            self.stdout.write(
                self.style.SUCCESS('🎥 VIDEOS ONLY mode - Skipping problematic articles')
            )
        
        if self.ultra_slow:
            self.stdout.write(
                self.style.SUCCESS(f'🐌 ULTRA SLOW mode - {self.video_delay}s delays')
            )
        
        self.stdout.write('🎯 Starting Conservative High-Success Recovery...')
        
        try:
            self.process_conservative_recovery()
        except Exception as e:
            raise CommandError(f'Recovery failed: {str(e)}')

    def process_conservative_recovery(self):
        """Conservative recovery focusing on what's most likely to work"""
        
        # Load CSV
        try:
            df = pd.read_csv(self.csv_file)
        except Exception as e:
            raise CommandError(f'❌ Error reading CSV file: {str(e)}')
        
        self.stdout.write(f'✅ Loaded {len(df)} questions from CSV')
        
        # Get or create dataset
        if not self.dry_run:
            self.dataset, created = ExpertQuestionDataset.objects.get_or_create(
                name=self.dataset_name,
                defaults={
                    'description': 'Research dataset with conservatively recovered source material',
                    'source_type': 'research',
                    'is_active': True
                }
            )
        
        # Identify candidates with highest success probability
        candidates = self.identify_high_success_candidates(df)
        
        if len(candidates) == 0:
            self.stdout.write('⚠️  No high-probability candidates found')
            return
        
        self.stdout.write(f'🎯 Processing {len(candidates)} high-probability candidates')
        
        # Process conservatively
        for idx, row in candidates.iterrows():
            self.process_conservative_question(df, idx, row)
            
            # Conservative delays
            time.sleep(self.video_delay)
        
        self.print_conservative_summary()

    def identify_high_success_candidates(self, df):
        """Identify questions with highest recovery success probability"""
        
        # Filter for missing source material
        missing_mask = (
            df['source_material'].isna() | 
            (df['source_material'] == 'null') | 
            (df['source_material'].str.strip() == '')
        )
        missing_questions = df[missing_mask].copy()
        
        self.stdout.write(f'📊 Found {len(missing_questions)} questions missing source material')
        
        # Prioritize by success probability
        high_success_candidates = []
        
        for idx, row in missing_questions.iterrows():
            success_score = self.calculate_success_probability(row)
            if success_score >= 0.7:  # Only high-probability candidates
                high_success_candidates.append((idx, row, success_score))
        
        # Sort by success probability (highest first)
        high_success_candidates.sort(key=lambda x: x[2], reverse=True)
        
        # Show analysis
        self.stdout.write('')
        self.stdout.write('📈 Success Probability Analysis:')
        
        video_candidates = [c for c in high_success_candidates if c[1]['source_type'] == 'Khan Academy Video']
        ted_candidates = [c for c in high_success_candidates if c[1]['source_type'] == 'TED-Ed']
        article_candidates = [c for c in high_success_candidates if c[1]['source_type'] == 'Khan Academy Article']
        
        self.stdout.write(f'  🎥 Khan Academy Videos: {len(video_candidates)} (High success rate)')
        self.stdout.write(f'  🎭 TED-Ed Videos: {len(ted_candidates)} (High success rate)')
        
        if not self.videos_only:
            self.stdout.write(f'  📄 Khan Academy Articles: {len(article_candidates)} (Low success rate - skipping in conservative mode)')
        
        # Return only video candidates for conservative approach
        if self.videos_only or True:  # Force videos only due to article issues
            result_candidates = pd.DataFrame([c[1] for c in video_candidates + ted_candidates])
            if len(result_candidates) > 0:
                result_candidates.index = [c[0] for c in video_candidates + ted_candidates]
        else:
            result_candidates = pd.DataFrame([c[1] for c in high_success_candidates])
            if len(result_candidates) > 0:
                result_candidates.index = [c[0] for c in high_success_candidates]
        
        return result_candidates

    def calculate_success_probability(self, row):
        """Calculate probability of successful recovery for a question"""
        
        score = 0.0
        
        # Video sources have higher success rates
        if row['source_type'] == 'Khan Academy Video' and pd.notna(row.get('video_id')):
            score += 0.8  # High base score for videos
            
            # Bonus for valid-looking video IDs
            video_id = str(row.get('video_id', ''))
            if len(video_id) == 11 and video_id.isalnum():  # Standard YouTube ID format
                score += 0.1
                
        elif row['source_type'] == 'TED-Ed' and pd.notna(row.get('video_youtube_link')):
            score += 0.8  # High base score for TED-Ed
            
            # Bonus for valid YouTube links
            link = str(row.get('video_youtube_link', ''))
            if 'youtube.com' in link or 'youtu.be' in link:
                score += 0.1
                
        elif row['source_type'] == 'Khan Academy Article' and pd.notna(row.get('article_id')):
            score += 0.3  # Lower base score due to URL issues
            
            # Penalty for problematic article ID formats
            article_id = str(row.get('article_id', ''))
            if article_id.startswith('x') and '_' in article_id:
                score -= 0.1  # These seem to be internal IDs
        
        return min(score, 1.0)

    def process_conservative_question(self, df, idx, row):
        """Process a single question conservatively"""
        
        question_id = row['question_id']
        source_type = row['source_type']
        
        self.stdout.write(f'🔄 Processing: {question_id} ({source_type})')
        
        try:
            recovered_source = None
            
            if source_type == 'Khan Academy Video':
                recovered_source = self.recover_video_conservative(row['video_id'])
            elif source_type == 'TED-Ed':
                recovered_source = self.recover_ted_conservative(row['video_youtube_link'])
            elif source_type == 'Khan Academy Article' and not self.videos_only:
                # Skip articles in conservative mode due to known issues
                self.stdout.write(f'  ⏭️  Skipping article (known URL issues)')
                self.skipped_count += 1
                return
            
            if recovered_source:
                # Update CSV
                df.at[idx, 'source_material'] = recovered_source
                
                # Update Django model
                if not self.dry_run:
                    self.update_django_model_conservative(row, recovered_source, True)
                
                self.recovered_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✅ SUCCESS! ({len(recovered_source)} chars)')
                )
            else:
                if not self.dry_run:
                    self.update_django_model_conservative(row, None, False)
                
                self.failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Failed (conservative attempt)')
                )
                
        except Exception as e:
            self.failed_count += 1
            self.stdout.write(
                self.style.ERROR(f'  💥 Error: {str(e)[:100]}...')
            )

    def recover_video_conservative(self, video_id):
        """Conservative video recovery with minimal API calls"""
        
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Single attempt with default language
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = ' '.join([entry['text'] for entry in transcript_list])
            
            if transcript_text.strip():
                # Basic cleaning
                cleaned_transcript = transcript_text.strip()
                if len(cleaned_transcript) > 8000:
                    cleaned_transcript = cleaned_transcript[:8000] + "..."
                return cleaned_transcript
            
            return None
            
        except ImportError:
            self.stdout.write(
                self.style.ERROR('❌ youtube-transcript-api not installed')
            )
            return None
        except Exception as e:
            if "Too Many Requests" in str(e):
                self.stdout.write(f'  🚦 Rate limited - stopping video recovery')
                raise  # Stop the whole process if rate limited
            return None

    def recover_ted_conservative(self, youtube_link):
        """Conservative TED-Ed recovery"""
        
        try:
            # Extract video ID
            video_id = None
            
            if 'youtube.com' in youtube_link and 'v=' in youtube_link:
                video_id = youtube_link.split('v=')[1].split('&')[0]
            elif 'youtu.be' in youtube_link:
                video_id = youtube_link.split('youtu.be/')[1].split('?')[0]
            
            if video_id:
                return self.recover_video_conservative(video_id)
            
            return None
            
        except Exception:
            return None

    def update_django_model_conservative(self, row, recovered_source, success):
        """Conservative Django model update"""
        
        try:
            with transaction.atomic():
                try:
                    expert_question = ExpertQuestion.objects.get(
                        question_id=row['question_id']
                    )
                    
                    if recovered_source:
                        expert_question.source_material = recovered_source
                        expert_question.is_missing_source = False
                    
                    expert_question.source_recovery_attempted = True
                    expert_question.source_recovery_date = timezone.now()
                    expert_question.save()
                    
                except ExpertQuestion.DoesNotExist:
                    # Create new question
                    ExpertQuestion.objects.create(
                        dataset=self.dataset,
                        question_id=row['question_id'],
                        question_text=row['question_text'],
                        question_type='MCQ',  # Default
                        source_material=recovered_source or '',
                        domain=row.get('domain', ''),
                        video_id=row.get('video_id', ''),
                        video_youtube_link=row.get('video_youtube_link', ''),
                        is_missing_source=not bool(recovered_source),
                        source_recovery_attempted=True,
                        source_recovery_date=timezone.now()
                    )
                
                return True
                
        except Exception as e:
            self.logger.error(f'Django update failed for {row["question_id"]}: {str(e)}')
            return False

    def print_conservative_summary(self):
        """Print conservative recovery summary"""
        
        total_processed = self.recovered_count + self.failed_count
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎯 CONSERVATIVE RECOVERY SUMMARY'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'📊 Total processed: {total_processed}')
        self.stdout.write(f'✅ Successfully recovered: {self.recovered_count}')
        self.stdout.write(f'❌ Failed recovery: {self.failed_count}')
        self.stdout.write(f'⏭️  Skipped (low probability): {self.skipped_count}')
        
        if total_processed > 0:
            success_rate = (self.recovered_count / total_processed) * 100
            self.stdout.write(f'📈 Success rate: {success_rate:.1f}%')
        
        if self.recovered_count >= 10:
            self.stdout.write(self.style.SUCCESS('🎉 EXCELLENT: Sufficient data for research!'))
        elif self.recovered_count >= 5:
            self.stdout.write(self.style.SUCCESS('✅ GOOD: Usable data for research'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  LIMITED: Consider alternative approaches'))
        
        self.stdout.write('')
        self.stdout.write('🔍 Next steps:')
        self.stdout.write('1. Wait for YouTube rate limits to reset (1 hour)')
        self.stdout.write('2. Try remaining high-probability questions')
        self.stdout.write('3. Consider manual recovery for critical articles')
        self.stdout.write('4. Proceed with available data for research')
        self.stdout.write('=' * 50)
