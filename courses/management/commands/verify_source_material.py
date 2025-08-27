from django.core.management.base import BaseCommand
from django.utils.html import format_html
from courses.models import ExpertQuestion, ExpertQuestionDataset
import pandas as pd
from collections import defaultdict


class Command(BaseCommand):
    help = 'Verify source material status with enhanced flag information'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file to verify'
        )
        parser.add_argument(
            '--dataset-name',
            type=str,
            default='LearningQ Research Sample',
            help='Name of the expert question dataset to check'
        )
        parser.add_argument(
            '--show-details',
            action='store_true',
            help='Show detailed information about missing questions'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dataset_name = options['dataset_name']
        show_details = options['show_details']
        
        self.stdout.write('🔍 Enhanced Source Material Verification')
        self.stdout.write('=' * 50)
        self.stdout.write(f'📄 CSV File: {csv_file}')
        self.stdout.write(f'📊 Dataset: {dataset_name}')
        self.stdout.write('')
        
        # Verify CSV
        csv_stats = self.verify_csv(csv_file, show_details)
        
        # Verify Django models
        django_stats = self.verify_django_models(dataset_name, show_details)
        
        # Cross-reference
        if csv_stats and django_stats:
            self.cross_reference_verification(csv_file, dataset_name)
        
        # Recovery recommendations
        self.provide_recommendations(csv_stats, django_stats)

    def verify_csv(self, csv_file, show_details=False):
        """Enhanced CSV verification with detailed flag analysis"""
        try:
            df = pd.read_csv(csv_file)
            
            # Check missing source material
            missing_mask = (
                df['source_material'].isna() | 
                (df['source_material'] == 'null') | 
                (df['source_material'].str.strip() == '')
            )
            
            missing_questions = df[missing_mask]
            complete_questions = df[~missing_mask]
            
            self.stdout.write(self.style.SUCCESS('📋 CSV VERIFICATION'))
            self.stdout.write(f'📊 Total questions: {len(df)}')
            self.stdout.write(f'✅ Questions with source material: {len(complete_questions)}')
            self.stdout.write(f'❌ Questions missing source material: {len(missing_questions)}')
            
            completion_rate = (len(complete_questions) / len(df)) * 100
            if completion_rate >= 90:
                style = self.style.SUCCESS
                emoji = '🎉'
            elif completion_rate >= 70:
                style = self.style.WARNING  
                emoji = '⚠️'
            else:
                style = self.style.ERROR
                emoji = '🚨'
            
            self.stdout.write(style(f'{emoji} Completion rate: {completion_rate:.1f}%'))
            
            # Detailed breakdown by source type
            self.stdout.write('')
            self.stdout.write('📈 Breakdown by source type:')
            source_breakdown = defaultdict(lambda: {'total': 0, 'missing': 0, 'questions': []})
            
            for _, row in df.iterrows():
                source_type = row['source_type']
                source_breakdown[source_type]['total'] += 1
                
                is_missing = (
                    pd.isna(row['source_material']) or 
                    row['source_material'] == 'null' or 
                    str(row['source_material']).strip() == ''
                )
                
                if is_missing:
                    source_breakdown[source_type]['missing'] += 1
                    source_breakdown[source_type]['questions'].append(row['question_id'])
            
            for source_type, stats in source_breakdown.items():
                completion_rate = ((stats['total'] - stats['missing']) / stats['total']) * 100
                status = '✅' if stats['missing'] == 0 else '❌' if completion_rate < 50 else '⚠️'
                
                self.stdout.write(
                    f'  {status} {source_type}: {stats["missing"]}/{stats["total"]} missing ({completion_rate:.1f}% complete)'
                )
                
                if show_details and stats['missing'] > 0:
                    sample_questions = stats['questions'][:3]
                    self.stdout.write(f'    Missing: {", ".join(sample_questions)}{"..." if len(stats["questions"]) > 3 else ""}')
            
            # Recovery potential analysis
            self.stdout.write('')
            self.stdout.write('🔧 Recovery Potential:')
            recoverable = 0
            for _, row in missing_questions.iterrows():
                if (
                    (row['source_type'] == 'Khan Academy Video' and pd.notna(row.get('video_id'))) or
                    (row['source_type'] == 'Khan Academy Article' and pd.notna(row.get('article_id'))) or
                    (row['source_type'] == 'TED-Ed' and pd.notna(row.get('video_youtube_link')))
                ):
                    recoverable += 1
            
            recovery_rate = (recoverable / len(missing_questions)) * 100 if missing_questions.shape[0] > 0 else 0
            self.stdout.write(f'  🎯 Recoverable questions: {recoverable}/{len(missing_questions)} ({recovery_rate:.1f}%)')
            
            self.stdout.write('')
            
            return {
                'total': len(df),
                'complete': len(complete_questions),
                'missing': len(missing_questions),
                'completion_rate': completion_rate,
                'recoverable': recoverable
            }
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error verifying CSV: {str(e)}'))
            return None

    def verify_django_models(self, dataset_name, show_details=False):
        """Enhanced Django model verification with flag analysis"""
        try:
            # Get dataset
            try:
                dataset = ExpertQuestionDataset.objects.get(name=dataset_name)
            except ExpertQuestionDataset.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Dataset "{dataset_name}" not found in Django models')
                )
                return None
            
            # Get questions with enhanced flag information
            questions = ExpertQuestion.objects.filter(dataset=dataset)
            total_questions = questions.count()
            
            if total_questions == 0:
                self.stdout.write(
                    self.style.WARNING('⚠️  No questions found in Django models')
                )
                return None
            
            # Analyze source material status
            questions_with_source = questions.filter(is_missing_source=False)
            questions_missing_source = questions.filter(is_missing_source=True)
            recovery_attempted = questions.filter(source_recovery_attempted=True)
            recovery_successful = recovery_attempted.filter(is_missing_source=False)
            recovery_failed = recovery_attempted.filter(is_missing_source=True)
            
            self.stdout.write(self.style.SUCCESS('🗃️  DJANGO MODELS VERIFICATION'))
            self.stdout.write(f'📊 Dataset: {dataset.name}')
            self.stdout.write(f'📊 Total questions in Django: {total_questions}')
            self.stdout.write(f'✅ Questions with source material: {questions_with_source.count()}')
            self.stdout.write(f'❌ Questions missing source material: {questions_missing_source.count()}')
            
            completion_rate = (questions_with_source.count() / total_questions) * 100
            self.stdout.write(f'📈 Completion rate: {completion_rate:.1f}%')
            
            # Recovery attempt statistics
            self.stdout.write('')
            self.stdout.write('🔄 Recovery Attempt Statistics:')
            self.stdout.write(f'  🎯 Recovery attempted: {recovery_attempted.count()}')
            self.stdout.write(f'  ✅ Recovery successful: {recovery_successful.count()}')
            self.stdout.write(f'  ❌ Recovery failed: {recovery_failed.count()}')
            
            if recovery_attempted.count() > 0:
                recovery_success_rate = (recovery_successful.count() / recovery_attempted.count()) * 100
                self.stdout.write(f'  📊 Recovery success rate: {recovery_success_rate:.1f}%')
            
            # Flag consistency check
            inconsistent_flags = questions.filter(
                is_missing_source=False, 
                source_material__in=['', None]
            ).count()
            
            if inconsistent_flags > 0:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  {inconsistent_flags} questions have inconsistent flags')
                )
            
            # Breakdown by domain
            self.stdout.write('')
            self.stdout.write('📈 Breakdown by domain:')
            domains = questions.values('domain').distinct()
            
            for domain_dict in domains:
                domain = domain_dict['domain'] or 'Unknown'
                domain_questions = questions.filter(domain=domain)
                domain_with_source = domain_questions.filter(is_missing_source=False)
                
                completion_rate = (domain_with_source.count() / domain_questions.count()) * 100
                missing_count = domain_questions.count() - domain_with_source.count()
                
                status = '✅' if missing_count == 0 else '❌' if completion_rate < 50 else '⚠️'
                self.stdout.write(
                    f'  {status} {domain}: {missing_count}/{domain_questions.count()} missing ({completion_rate:.1f}% complete)'
                )
                
                if show_details and missing_count > 0:
                    sample_missing = domain_questions.filter(is_missing_source=True)[:3]
                    missing_ids = [q.question_id for q in sample_missing]
                    self.stdout.write(f'    Missing: {", ".join(missing_ids)}{"..." if missing_count > 3 else ""}')
            
            self.stdout.write('')
            
            return {
                'total': total_questions,
                'complete': questions_with_source.count(),
                'missing': questions_missing_source.count(),
                'completion_rate': completion_rate,
                'recovery_attempted': recovery_attempted.count(),
                'recovery_successful': recovery_successful.count(),
                'recovery_failed': recovery_failed.count()
            }
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error verifying Django models: {str(e)}'))
            return None

    def cross_reference_verification(self, csv_file, dataset_name):
        """Enhanced cross-reference with flag consistency"""
        try:
            # Load CSV
            df = pd.read_csv(csv_file)
            csv_question_ids = set(df['question_id'].tolist())
            
            # Get Django questions
            try:
                dataset = ExpertQuestionDataset.objects.get(name=dataset_name)
                django_questions = ExpertQuestion.objects.filter(dataset=dataset)
                django_question_ids = set(django_questions.values_list('question_id', flat=True))
            except ExpertQuestionDataset.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING('⚠️  Cannot cross-reference: Django dataset not found')
                )
                return
            
            # Compare
            in_csv_only = csv_question_ids - django_question_ids
            in_django_only = django_question_ids - csv_question_ids
            in_both = csv_question_ids & django_question_ids
            
            self.stdout.write(self.style.SUCCESS('🔗 CROSS-REFERENCE VERIFICATION'))
            self.stdout.write(f'📄 Questions in CSV only: {len(in_csv_only)}')
            self.stdout.write(f'🗃️  Questions in Django only: {len(in_django_only)}')
            self.stdout.write(f'🤝 Questions in both: {len(in_both)}')
            
            sync_rate = (len(in_both) / len(csv_question_ids)) * 100
            self.stdout.write(f'🔄 Sync rate: {sync_rate:.1f}%')
            
            # Check source material consistency for common questions
            if in_both:
                consistency_issues = 0
                flag_mismatches = 0
                
                sample_size = min(len(in_both), 20)  # Check sample for performance
                for qid in list(in_both)[:sample_size]:
                    csv_row = df[df['question_id'] == qid].iloc[0]
                    django_question = django_questions.get(question_id=qid)
                    
                    csv_has_source = (
                        pd.notna(csv_row['source_material']) and 
                        csv_row['source_material'] != 'null' and 
                        str(csv_row['source_material']).strip() != ''
                    )
                    django_has_source = bool(django_question.source_material and django_question.source_material.strip())
                    django_flag_says_has_source = not django_question.is_missing_source
                    
                    if csv_has_source != django_has_source:
                        consistency_issues += 1
                    
                    if django_has_source != django_flag_says_has_source:
                        flag_mismatches += 1
                
                self.stdout.write('')
                self.stdout.write(f'🔍 Source material consistency (sample of {sample_size}):')
                self.stdout.write(f'  📊 CSV ↔ Django inconsistencies: {consistency_issues}')
                self.stdout.write(f'  🏷️  Django flag mismatches: {flag_mismatches}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error in cross-reference verification: {str(e)}'))

    def provide_recommendations(self, csv_stats, django_stats):
        """Provide actionable recommendations based on verification results"""
        self.stdout.write(self.style.SUCCESS('💡 RECOMMENDATIONS'))
        
        if not csv_stats and not django_stats:
            self.stdout.write('❌ No statistics available to provide recommendations')
            return
        
        if csv_stats and csv_stats['missing'] > 0:
            self.stdout.write(f'1. 🔧 Run source recovery for {csv_stats["missing"]} missing questions:')
            self.stdout.write('   python manage.py recover_source_material learningq_research_sample.csv')
            
            if csv_stats['recoverable'] > 0:
                self.stdout.write(f'   💪 {csv_stats["recoverable"]} questions are likely recoverable')
        
        if django_stats:
            if django_stats['recovery_failed'] > 0:
                self.stdout.write(f'2. 🔄 Retry failed recoveries for {django_stats["recovery_failed"]} questions:')
                self.stdout.write('   python manage.py recover_source_material learningq_research_sample.csv --force-retry')
            
            if django_stats['completion_rate'] >= 85:
                self.stdout.write('3. ✅ Dataset quality is good for AI question generation research')
            elif django_stats['completion_rate'] >= 70:
                self.stdout.write('3. ⚠️  Consider improving source material coverage before research')
            else:
                self.stdout.write('3. 🚨 Source material coverage is too low for reliable research')
        
        self.stdout.write('4. 🎯 Check Django admin for visual source material status')
        self.stdout.write('5. 📊 Use complete questions for your LearningQ research comparison')
        self.stdout.write('')
