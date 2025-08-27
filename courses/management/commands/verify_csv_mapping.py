import os
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Count, Q
from courses.models import ExpertQuestion

class Command(BaseCommand):
    help = 'Verify CSV mapping to ExpertQuestion model (before creating AI questions)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='research_source_materials.csv',
            help='CSV file name in project root'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed analysis of each question'
        )
        parser.add_argument(
            '--range',
            type=str,
            help='Specify range to check (e.g., "1-10", "11-20")'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        detailed = options['detailed']
        range_str = options.get('range')
        
        # Load CSV
        csv_path = os.path.join(settings.BASE_DIR, csv_file)
        if not os.path.exists(csv_path):
            raise CommandError(f'CSV file not found: {csv_path}')
        
        self.stdout.write(f'📊 Loading CSV: {csv_file}')
        df = pd.read_csv(csv_path)
        
        # Apply range filter if specified
        if range_str:
            start, end = map(int, range_str.split('-'))
            df = df.iloc[start-1:end]  # Convert to 0-based indexing
            self.stdout.write(f'🎯 Checking rows {start}-{end} ({len(df)} questions)')
        
        # Analysis
        self.stdout.write(f'\n🔍 CSV Analysis:')
        self.stdout.write(f'Questions to verify: {len(df)}')
        
        # Check domains
        domain_counts = df['domain'].value_counts()
        self.stdout.write(f'\nDomain distribution:')
        for domain, count in domain_counts.items():
            self.stdout.write(f'  {domain}: {count}')
        
        # Check question types
        type_counts = df['question_type'].value_counts()
        self.stdout.write(f'\nQuestion type distribution:')
        for qtype, count in type_counts.items():
            self.stdout.write(f'  {qtype}: {count}')
        
        # Verify mapping to ExpertQuestion model
        self.stdout.write(f'\n🔗 Mapping Verification:')
        
        matched_questions = []
        unmatched_questions = []
        missing_source_material = []
        data_mismatches = []
        
        for idx, row in df.iterrows():
            question_id = row['question_id']
            
            try:
                expert_q = ExpertQuestion.objects.get(question_id=question_id)
                
                # Check data consistency
                mismatches = []
                if str(row['domain']).strip() != expert_q.domain:
                    mismatches.append(f"Domain: CSV='{row['domain']}' vs DB='{expert_q.domain}'")
                if str(row['question_type']).strip() != expert_q.question_type:
                    mismatches.append(f"Type: CSV='{row['question_type']}' vs DB='{expert_q.question_type}'")
                
                match_data = {
                    'csv_row': row,
                    'expert_question': expert_q,
                    'has_source_material': bool(expert_q.source_material and len(expert_q.source_material.strip()) > 50),
                    'mismatches': mismatches
                }
                matched_questions.append(match_data)
                
                if mismatches:
                    data_mismatches.append({
                        'question_id': question_id,
                        'mismatches': mismatches
                    })
                
                if not expert_q.source_material or len(expert_q.source_material.strip()) < 50:
                    missing_source_material.append(question_id)
                    
            except ExpertQuestion.DoesNotExist:
                unmatched_questions.append(question_id)
        
        # Results
        self.stdout.write(f'✅ Successfully mapped: {len(matched_questions)}/{len(df)}')
        self.stdout.write(f'❌ Unmatched questions: {len(unmatched_questions)}')
        self.stdout.write(f'⚠️  Missing source material: {len(missing_source_material)}')
        self.stdout.write(f'🔄 Data mismatches: {len(data_mismatches)}')
        
        # Show issues
        if unmatched_questions:
            self.stdout.write(f'\n❌ Unmatched question IDs:')
            for qid in unmatched_questions[:5]:
                self.stdout.write(f'  • {qid}')
            if len(unmatched_questions) > 5:
                self.stdout.write(f'  ... and {len(unmatched_questions) - 5} more')
        
        if missing_source_material:
            self.stdout.write(f'\n⚠️  Questions missing source material:')
            for qid in missing_source_material[:5]:
                self.stdout.write(f'  • {qid}')
        
        if data_mismatches:
            self.stdout.write(f'\n🔄 Data mismatches found:')
            for mismatch in data_mismatches[:3]:
                self.stdout.write(f'  • {mismatch["question_id"]}: {"; ".join(mismatch["mismatches"])}')
        
        # Detailed analysis
        if detailed and len(df) <= 10:
            self.show_detailed_analysis(matched_questions)
        elif detailed:
            self.stdout.write(
                self.style.WARNING('Too many questions for detailed view. Use --range to limit scope.')
            )
        
        # Assessment
        usable_questions = len([m for m in matched_questions if m['has_source_material'] and not m['mismatches']])
        readiness_score = (usable_questions / len(df) * 100) if len(df) > 0 else 0
        
        self.stdout.write(f'\n🎯 Batch Readiness Assessment:')
        self.stdout.write(f'Usable questions: {usable_questions}/{len(df)}')
        self.stdout.write(f'Readiness score: {readiness_score:.1f}%')
        
        if readiness_score >= 90:
            self.stdout.write(self.style.SUCCESS('🟢 EXCELLENT - Ready for generation'))
        elif readiness_score >= 80:
            self.stdout.write(self.style.SUCCESS('🟡 GOOD - Minor issues, ready to proceed'))
        elif readiness_score >= 70:
            self.stdout.write(self.style.WARNING('🟠 FAIR - Some issues need attention'))
        else:
            self.stdout.write(self.style.ERROR('🔴 POOR - Fix issues before proceeding'))
    
    def show_detailed_analysis(self, matched_questions):
        """Show detailed question-by-question analysis"""
        self.stdout.write(f'\n📝 Detailed Analysis:')
        
        for i, match in enumerate(matched_questions):
            csv_row = match['csv_row']
            expert_q = match['expert_question']
            
            self.stdout.write(f'\n--- Question {i+1}: {csv_row["question_id"]} ---')
            self.stdout.write(f'Domain: {csv_row["domain"]}')
            self.stdout.write(f'Type: {csv_row["question_type"]}')
            self.stdout.write(f'Source Material Length: {len(str(csv_row["source_material"]))} chars')
            self.stdout.write(f'Expert Question: {expert_q.question_text[:100]}...')
            self.stdout.write(f'Target Question: {str(csv_row["target_question"])[:100]}...')
            
            if match['mismatches']:
                self.stdout.write(self.style.WARNING(f'⚠️  Issues: {"; ".join(match["mismatches"])}'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ Ready for generation'))

