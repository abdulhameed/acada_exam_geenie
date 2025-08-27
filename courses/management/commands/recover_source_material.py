# Replace your existing courses/management/commands/recover_source_material.py with this enhanced version

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from courses.models import ExpertQuestion, ExpertQuestionDataset
import pandas as pd
import requests
import time
import re
import logging
from typing import Optional, Dict, List
import os
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Enhanced source material recovery with rate limiting and fallback strategies'

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
            '--limit',
            type=int,
            help='Limit the number of questions to process (for testing)'
        )
        parser.add_argument(
            '--force-retry',
            action='store_true',
            help='Retry recovery for questions that previously failed'
        )
        parser.add_argument(
            '--slow-mode',
            action='store_true',
            help='Use slower rate limiting to avoid API limits'
        )
        parser.add_argument(
            '--skip-youtube',
            action='store_true',
            help='Skip YouTube transcript recovery (use for testing articles only)'
        )

    def handle(self, *args, **options):
        self.csv_file = options['csv_file']
        self.dataset_name = options['dataset_name']
        self.dry_run = options['dry_run']
        self.limit = options['limit']
        self.force_retry = options['force_retry']
        self.slow_mode = options['slow_mode']
        self.skip_youtube = options['skip_youtube']
        
        # Enhanced rate limiting settings
        self.youtube_delay = 3.0 if self.slow_mode else 1.5  # Seconds between YouTube requests
        self.article_delay = 1.0 if self.slow_mode else 0.5   # Seconds between article requests
        self.max_retries = 3
        self.retry_delays = [5, 15, 30]  # Exponential backoff
        
        # Setup enhanced logging
        self.setup_logging()
        
        # Initialize counters
        self.recovered_count = 0
        self.failed_count = 0
        self.updated_models = 0
        self.skipped_count = 0
        self.rate_limited_count = 0
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 Running in DRY RUN mode - no database changes will be made')
            )
        
        if self.slow_mode:
            self.stdout.write(
                self.style.SUCCESS('🐌 Slow mode enabled - using conservative rate limiting')
            )
        
        if self.skip_youtube:
            self.stdout.write(
                self.style.WARNING('⏭️  Skipping YouTube transcript recovery')
            )
        
        self.stdout.write('🚀 Starting Enhanced Source Material Recovery with Rate Limiting...')
        
        try:
            self.process_recovery()
        except Exception as e:
            raise CommandError(f'Recovery failed: {str(e)}')

    def setup_logging(self):
        """Setup enhanced logging with file output"""
        log_filename = f'source_recovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.stdout.write(f'📝 Detailed logs will be saved to: {log_filename}')

    def process_recovery(self):
        """Enhanced recovery process with better error handling"""
        self.stdout.write(f'📄 Loading CSV file: {self.csv_file}')
        
        if not os.path.exists(self.csv_file):
            raise CommandError(f'❌ CSV file not found: {self.csv_file}')
        
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
                    'description': 'Research dataset with recovered source material',
                    'source_type': 'research',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'🆕 Created new dataset: {self.dataset_name}')
        
        # Update missing source flags
        self.update_missing_source_flags(df)
        
        # Identify questions needing recovery
        missing_questions = self.identify_recovery_candidates(df)
        
        if len(missing_questions) == 0:
            self.stdout.write('✨ No questions need recovery. Exiting.')
            self.print_summary()
            return
        
        # Group questions by source type for optimized processing
        grouped_questions = self.group_questions_by_source_type(missing_questions)
        
        # Process each group with appropriate strategy
        self.process_grouped_questions(df, grouped_questions)
        
        # Save updated CSV
        if not self.dry_run:
            output_path = self.csv_file.replace('.csv', '_recovered.csv')
            df.to_csv(output_path, index=False)
            self.stdout.write(f'💾 Updated CSV saved to: {output_path}')
        
        self.print_summary()

    def identify_recovery_candidates(self, df):
        """Identify questions that need recovery with smart filtering"""
        missing_mask = (
            df['source_material'].isna() | 
            (df['source_material'] == 'null') | 
            (df['source_material'].str.strip() == '')
        )
        missing_questions = df[missing_mask].copy()
        
        # Filter based on retry policy
        if not self.force_retry and not self.dry_run:
            attempted_questions = set(
                ExpertQuestion.objects.filter(
                    source_recovery_attempted=True,
                    dataset=self.dataset
                ).values_list('question_id', flat=True)
            )
            
            missing_questions = missing_questions[
                ~missing_questions['question_id'].isin(attempted_questions)
            ]
            
            if len(attempted_questions) > 0:
                self.stdout.write(
                    f'⏭️  Skipping {len(attempted_questions)} questions with previous recovery attempts. '
                    f'Use --force-retry to retry them.'
                )
        
        if self.limit:
            missing_questions = missing_questions.head(self.limit)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🎯 Found {len(missing_questions)} questions to process'
            )
        )
        
        return missing_questions

    def group_questions_by_source_type(self, missing_questions):
        """Group questions by source type for optimized processing"""
        grouped = {
            'khan_videos': [],
            'khan_articles': [],
            'ted_ed': []
        }
        
        for idx, row in missing_questions.iterrows():
            if row['source_type'] == 'Khan Academy Video' and pd.notna(row.get('video_id')):
                if not self.skip_youtube:
                    grouped['khan_videos'].append((idx, row))
            elif row['source_type'] == 'Khan Academy Article' and pd.notna(row.get('article_id')):
                grouped['khan_articles'].append((idx, row))
            elif row['source_type'] == 'TED-Ed' and pd.notna(row.get('video_youtube_link')):
                if not self.skip_youtube:
                    grouped['ted_ed'].append((idx, row))
        
        # Log processing plan
        self.stdout.write('')
        self.stdout.write('📋 Processing Plan:')
        self.stdout.write(f'  🎥 Khan Academy Videos: {len(grouped["khan_videos"])}')
        self.stdout.write(f'  📄 Khan Academy Articles: {len(grouped["khan_articles"])}')
        self.stdout.write(f'  🎭 TED-Ed Videos: {len(grouped["ted_ed"])}')
        self.stdout.write('')
        
        return grouped

    def process_grouped_questions(self, df, grouped_questions):
        """Process questions by group with appropriate delays"""
        
        # Process Khan Academy Articles first (usually more reliable)
        if grouped_questions['khan_articles']:
            self.stdout.write('📄 Processing Khan Academy Articles...')
            for idx, row in grouped_questions['khan_articles']:
                self.process_single_question(df, idx, row, 'article')
                time.sleep(self.article_delay + random.uniform(0, 0.5))  # Random jitter
        
        # Process Khan Academy Videos with YouTube API
        if grouped_questions['khan_videos']:
            self.stdout.write('🎥 Processing Khan Academy Videos...')
            self.stdout.write(f'   ⏱️  Using {self.youtube_delay}s delays between requests...')
            
            for idx, row in grouped_questions['khan_videos']:
                self.process_single_question(df, idx, row, 'video')
                time.sleep(self.youtube_delay + random.uniform(0, 1))  # Longer delay for YouTube
        
        # Process TED-Ed Videos
        if grouped_questions['ted_ed']:
            self.stdout.write('🎭 Processing TED-Ed Videos...')
            for idx, row in grouped_questions['ted_ed']:
                self.process_single_question(df, idx, row, 'ted_ed')
                time.sleep(self.youtube_delay + random.uniform(0, 1))

    def process_single_question(self, df: pd.DataFrame, idx: int, row: pd.Series, source_hint: str):
        """Process single question with retry logic and better error handling"""
        question_id = row['question_id']
        
        self.stdout.write(f'🔄 Processing: {question_id} ({source_hint})')
        
        for attempt in range(self.max_retries):
            try:
                recovered_source = None
                
                # Attempt recovery based on source type
                if source_hint == 'video' and row['source_type'] == 'Khan Academy Video':
                    recovered_source = self.recover_khan_video_transcript_with_retry(row['video_id'])
                    
                elif source_hint == 'article' and row['source_type'] == 'Khan Academy Article':
                    recovered_source = self.recover_khan_article_content_enhanced(row['article_id'])
                    
                elif source_hint == 'ted_ed' and row['source_type'] == 'TED-Ed':
                    recovered_source = self.recover_ted_transcript_with_retry(row['video_youtube_link'])
                
                if recovered_source:
                    # Success!
                    df.at[idx, 'source_material'] = recovered_source
                    
                    if not self.dry_run:
                        model_updated = self.update_django_model(row, recovered_source, success=True)
                        if model_updated:
                            self.updated_models += 1
                    
                    self.recovered_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✅ Recovered ({len(recovered_source)} chars) - Attempt {attempt + 1}')
                    )
                    return  # Success, exit retry loop
                
                # If we get here, recovery failed but no exception
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    self.stdout.write(f'  ⏳ Attempt {attempt + 1} failed, retrying in {delay}s...')
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    if not self.dry_run:
                        self.update_django_model(row, None, success=False)
                    self.failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ All {self.max_retries} attempts failed')
                    )
                
            except Exception as e:
                if "Too Many Requests" in str(e) or "429" in str(e):
                    self.rate_limited_count += 1
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt] * 2  # Double delay for rate limiting
                        self.stdout.write(f'  🚦 Rate limited, waiting {delay}s before retry...')
                        time.sleep(delay)
                    else:
                        self.stdout.write(f'  🚦 Rate limited - all retries exhausted')
                        if not self.dry_run:
                            self.update_django_model(row, None, success=False)
                        self.failed_count += 1
                        return
                else:
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        self.stdout.write(f'  💥 Error (attempt {attempt + 1}): {str(e)[:100]}... Retrying in {delay}s')
                        time.sleep(delay)
                    else:
                        if not self.dry_run:
                            self.update_django_model(row, None, success=False)
                        self.failed_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'  💥 Final error: {str(e)[:100]}...')
                        )

    def recover_khan_video_transcript_with_retry(self, video_id: str) -> Optional[str]:
        """Enhanced YouTube transcript recovery with better error handling"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
            
            # Try multiple language options
            language_codes = ['en', 'en-US', 'en-GB', 'en-CA']
            
            for lang_code in language_codes:
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang_code])
                    transcript_text = ' '.join([entry['text'] for entry in transcript_list])
                    
                    if transcript_text.strip():
                        cleaned_transcript = self.clean_transcript_text(transcript_text)
                        if len(cleaned_transcript) > 8000:
                            cleaned_transcript = cleaned_transcript[:8000] + "..."
                        return cleaned_transcript
                        
                except (TranscriptsDisabled, NoTranscriptFound):
                    continue  # Try next language
                except Exception as e:
                    if "Too Many Requests" in str(e):
                        raise  # Re-raise rate limiting errors
                    continue  # Try next language
            
            # If no transcript found in any language, try auto-generated
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                transcript_text = ' '.join([entry['text'] for entry in transcript_list])
                
                if transcript_text.strip():
                    cleaned_transcript = self.clean_transcript_text(transcript_text)
                    if len(cleaned_transcript) > 8000:
                        cleaned_transcript = cleaned_transcript[:8000] + "..."
                    return cleaned_transcript
                    
            except Exception:
                pass
            
            return None
            
        except ImportError:
            self.stdout.write(
                self.style.ERROR('❌ youtube-transcript-api not installed. Run: pip install youtube-transcript-api')
            )
            return None
        except Exception as e:
            if "Too Many Requests" in str(e):
                raise  # Re-raise for retry logic
            self.logger.warning(f'YouTube transcript failed for {video_id}: {str(e)}')
            return None

    def recover_khan_article_content_enhanced(self, article_id: str) -> Optional[str]:
        """Enhanced Khan Academy article recovery with multiple strategies"""
        try:
            # Strategy 1: Try multiple URL patterns
            url_patterns = [
                f"https://www.khanacademy.org/science/article/{article_id}",
                f"https://www.khanacademy.org/math/article/{article_id}",
                f"https://www.khanacademy.org/humanities/article/{article_id}",
                f"https://www.khanacademy.org/computing/article/{article_id}",
                f"https://www.khanacademy.org/economics-finance-domain/article/{article_id}",
                f"https://www.khanacademy.org/test-prep/article/{article_id}",
                f"https://www.khanacademy.org/article/{article_id}",
                # Try without 'article' path
                f"https://www.khanacademy.org/science/{article_id}",
                f"https://www.khanacademy.org/math/{article_id}",
                f"https://www.khanacademy.org/humanities/{article_id}",
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            for url in url_patterns:
                try:
                    response = requests.get(
                        url, 
                        timeout=20, 
                        headers=headers,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        content = self.extract_khan_content(response.text, article_id)
                        if content and len(content.strip()) > 200:  # Minimum content length
                            return content
                    
                    elif response.status_code == 429:
                        raise Exception("Too Many Requests - Khan Academy rate limited")
                        
                except requests.RequestException as e:
                    if "429" in str(e):
                        raise Exception("Too Many Requests")
                    continue
            
            # Strategy 2: Try Khan Academy API (if available)
            api_content = self.try_khan_api_approach(article_id)
            if api_content:
                return api_content
            
            return None
            
        except Exception as e:
            if "Too Many Requests" in str(e):
                raise  # Re-raise for retry logic
            self.logger.error(f'Enhanced article recovery failed for {article_id}: {str(e)}')
            return None

    def extract_khan_content(self, html_content: str, article_id: str) -> Optional[str]:
        """Extract content from Khan Academy HTML with multiple selectors"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try multiple content selectors (Khan Academy structure changes over time)
            content_selectors = [
                # Modern selectors
                '[data-test-id="article-content"]',
                '.article-content-container',
                '.perseus-renderer',
                '.framework-perseus',
                
                # Legacy selectors
                '.article-content',
                '.main-content',
                '.markdown-rendered-content',
                '.article-body',
                
                # Fallback selectors
                'main',
                '.content',
                '#content',
                
                # Very specific Khan Academy selectors
                '[class*="article"]',
                '[class*="content"]',
                '[class*="perseus"]'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text(separator=' ', strip=True) for elem in elements])
                    if len(content.strip()) > 200:  # Found substantial content
                        break
            
            # If still no good content, try extracting all paragraphs
            if not content or len(content.strip()) < 200:
                paragraphs = soup.find_all(['p', 'div'], string=True)
                content = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            if content and len(content.strip()) > 200:
                cleaned_content = self.clean_article_text(content)
                if len(cleaned_content) > 8000:
                    cleaned_content = cleaned_content[:8000] + "..."
                return cleaned_content
            
            return None
            
        except ImportError:
            self.stdout.write(
                self.style.ERROR('❌ beautifulsoup4 not installed. Run: pip install beautifulsoup4')
            )
            return None
        except Exception as e:
            self.logger.error(f'Content extraction failed for {article_id}: {str(e)}')
            return None

    def try_khan_api_approach(self, article_id: str) -> Optional[str]:
        """Try alternative Khan Academy API approach (placeholder for future implementation)"""
        # This could be implemented if Khan Academy provides an API
        # For now, return None
        return None

    def recover_ted_transcript_with_retry(self, youtube_link: str) -> Optional[str]:
        """Enhanced TED-Ed transcript recovery"""
        try:
            # Extract video ID from various YouTube URL formats
            video_id = None
            
            if 'youtube.com' in youtube_link:
                if 'v=' in youtube_link:
                    video_id = youtube_link.split('v=')[1].split('&')[0]
                elif '/embed/' in youtube_link:
                    video_id = youtube_link.split('/embed/')[1].split('?')[0]
                elif '/watch/' in youtube_link:
                    video_id = youtube_link.split('/watch/')[1].split('?')[0]
            elif 'youtu.be' in youtube_link:
                video_id = youtube_link.split('youtu.be/')[1].split('?')[0]
            
            if video_id:
                return self.recover_khan_video_transcript_with_retry(video_id)
            else:
                self.logger.warning(f'Could not extract video ID from {youtube_link}')
                return None
                
        except Exception as e:
            self.logger.error(f'TED-Ed recovery failed for {youtube_link}: {str(e)}')
            return None

    def update_missing_source_flags(self, df):
        """Update missing source flags for all questions"""
        if self.dry_run:
            return
        
        self.stdout.write('🏷️  Updating missing source flags...')
        
        total_updated = 0
        for _, row in df.iterrows():
            try:
                question = ExpertQuestion.objects.get(question_id=row['question_id'])
                
                has_source = bool(
                    row['source_material'] and 
                    pd.notna(row['source_material']) and 
                    str(row['source_material']).strip() != '' and 
                    str(row['source_material']) != 'null'
                )
                
                question.is_missing_source = not has_source
                question.save()
                total_updated += 1
                
            except ExpertQuestion.DoesNotExist:
                pass
        
        self.stdout.write(f'✅ Updated flags for {total_updated} existing questions')

    def update_django_model(self, row: pd.Series, recovered_source: Optional[str], success: bool) -> bool:
        """Update Django model with enhanced error handling"""
        try:
            with transaction.atomic():
                try:
                    expert_question = ExpertQuestion.objects.get(
                        question_id=row['question_id']
                    )
                    
                    if recovered_source:
                        expert_question.source_material = recovered_source
                        expert_question.is_missing_source = False
                    else:
                        expert_question.is_missing_source = True
                    
                    expert_question.source_recovery_attempted = True
                    expert_question.source_recovery_date = timezone.now()
                    expert_question.save()
                    
                except ExpertQuestion.DoesNotExist:
                    expert_question = ExpertQuestion.objects.create(
                        dataset=self.dataset,
                        question_id=row['question_id'],
                        question_text=row['question_text'],
                        question_type=self.map_question_type(row['question_type']),
                        source_material=recovered_source or '',
                        domain=row.get('domain', ''),
                        difficulty_level=self.map_difficulty_level(row.get('difficulty_level')),
                        video_title=row.get('video_title', ''),
                        video_youtube_link=row.get('video_youtube_link', ''),
                        video_id=row.get('video_id', ''),
                        file_source=row.get('file_source', ''),
                        times_used_as_template=0,
                        is_missing_source=not bool(recovered_source),
                        source_recovery_attempted=True,
                        source_recovery_date=timezone.now()
                    )
                
                return True
                
        except Exception as e:
            self.logger.error(f'Django model update failed for {row["question_id"]}: {str(e)}')
            return False

    def map_question_type(self, question_type: str) -> str:
        """Map question type to Django choices"""
        mapping = {
            'MCQ': 'MCQ',
            'ESSAY': 'ESSAY',
            'SHORT_ANSWER': 'SHORT_ANSWER',
            'TRUE_FALSE': 'TRUE_FALSE'
        }
        return mapping.get(question_type, 'MCQ')

    def map_difficulty_level(self, difficulty) -> str:
        """Map difficulty level to Django choices"""
        if pd.isna(difficulty) or not difficulty:
            return 'unknown'
        
        difficulty_lower = str(difficulty).lower()
        mapping = {
            'easy': 'easy',
            'medium': 'medium',
            'hard': 'hard',
            'beginner': 'easy',
            'intermediate': 'medium',
            'advanced': 'hard'
        }
        return mapping.get(difficulty_lower, 'unknown')

    def clean_transcript_text(self, text: str) -> str:
        """Enhanced transcript cleaning"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove timestamps
        text = re.sub(r'\d+:\d+', '', text)
        
        # Remove common transcript artifacts
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'<.*?>', '', text)
        
        # Remove repeated phrases common in auto-generated transcripts
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text)  # Remove word repetitions
        
        return text.strip()

    def clean_article_text(self, text: str) -> str:
        """Enhanced article text cleaning"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common HTML artifacts
        text = re.sub(r'\xa0', ' ', text)  # Non-breaking spaces
        text = re.sub(r'\u200b', '', text)  # Zero-width spaces
        text = re.sub(r'\u2019', "'", text)  # Smart quotes
        text = re.sub(r'\u201c|\u201d', '"', text)  # Smart quotes
        
        # Remove navigation and UI text
        ui_patterns = [
            r'Sign up|Log in|Sign in',
            r'Khan Academy|khanacademy\.org',
            r'Next lesson|Previous lesson',
            r'Share|Tweet|Facebook',
            r'Menu|Navigation|Search',
            r'Loading\.\.\.',
            r'Click here|Learn more',
        ]
        
        for pattern in ui_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()

    def print_summary(self):
        """Enhanced summary with detailed statistics"""
        total_processed = self.recovered_count + self.failed_count
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎉 ENHANCED RECOVERY SUMMARY'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'📊 Total processed: {total_processed}')
        self.stdout.write(f'✅ Successfully recovered: {self.recovered_count}')
        self.stdout.write(f'❌ Failed recovery: {self.failed_count}')
        self.stdout.write(f'🚦 Rate limited: {self.rate_limited_count}')
        self.stdout.write(f'🏷️  Django models updated: {self.updated_models}')
        
        if total_processed > 0:
            success_rate = (self.recovered_count / total_processed) * 100
            self.stdout.write(f'📈 Success rate: {success_rate:.1f}%')
        
        self.stdout.write('')
        
        if self.rate_limited_count > 0:
            self.stdout.write('🚦 Rate Limiting Detected!')
            self.stdout.write('   Consider using --slow-mode for better success rates')
            self.stdout.write('   Or try again later when rate limits reset')
        
        if self.failed_count > 0:
            self.stdout.write('🔧 Recovery Tips:')
            self.stdout.write('   1. Try --slow-mode for conservative rate limiting')
            self.stdout.write('   2. Use --skip-youtube to test article recovery only')
            self.stdout.write('   3. Run with --force-retry to retry failed questions')
            self.stdout.write('   4. Check the log file for detailed error information')
        
        self.stdout.write('')
        self.stdout.write('🔍 Next steps:')
        self.stdout.write('1. Check Django admin for updated source material flags')
        self.stdout.write('2. Run verification command to confirm results')
        self.stdout.write('3. Use updated dataset for AI question generation')
        self.stdout.write('=' * 60)
