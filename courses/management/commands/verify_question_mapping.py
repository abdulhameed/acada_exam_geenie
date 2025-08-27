import os
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Count, Q
from courses.models import ExpertQuestion, AIGeneratedQuestion


class Command(BaseCommand):
    help = 'Verify mapping between CSV questions and ExpertQuestion model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='research_source_materials.csv',
            help='CSV file name in project root'
        )
        parser.add_argument(
            '--fix-mapping',
            action='store_true',
            help='Attempt to fix any mapping issues found'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed analysis of each question'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        fix_mapping = options['fix_mapping']
        detailed = options['detailed']
        
        # Load CSV
        csv_path = os.path.join(settings.BASE_DIR, csv_file)
        if not os.path.exists(csv_path):
            raise CommandError(f'CSV file not found: {csv_path}')
        
        self.stdout.write(f'📊 Loading CSV: {csv_file}')
        df = pd.read_csv(csv_path)
        
        # Analysis
        self.stdout.write(f'\n🔍 CSV Analysis:')
        self.stdout.write(f'Total questions in CSV: {len(df)}')
        
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
        
        for _, row in df.iterrows():
            question_id = row['question_id']
            
            try:
                expert_q = ExpertQuestion.objects.get(question_id=question_id)
                matched_questions.append({
                    'csv_row': row,
                    'expert_question': expert_q,
                    'has_source_material': bool(expert_q.source_material and len(expert_q.source_material.strip()) > 50)
                })
                
                if not expert_q.source_material or len(expert_q.source_material.strip()) < 50:
                    missing_source_material.append(question_id)
                    
            except ExpertQuestion.DoesNotExist:
                unmatched_questions.append(question_id)
        
        # Results
        self.stdout.write(f'✅ Successfully mapped: {len(matched_questions)}/{len(df)}')
        self.stdout.write(f'❌ Unmatched questions: {len(unmatched_questions)}')
        self.stdout.write(f'⚠️  Missing source material: {len(missing_source_material)}')
        
        if unmatched_questions:
            self.stdout.write(f'\n❌ Unmatched question IDs:')
            for qid in unmatched_questions[:10]:  # Show first 10
                self.stdout.write(f'  • {qid}')
            if len(unmatched_questions) > 10:
                self.stdout.write(f'  ... and {len(unmatched_questions) - 10} more')
        
        if missing_source_material:
            self.stdout.write(f'\n⚠️  Questions missing source material:')
            for qid in missing_source_material[:10]:
                self.stdout.write(f'  • {qid}')
            if len(missing_source_material) > 10:
                self.stdout.write(f'  ... and {len(missing_source_material) - 10} more')
        
        # Detailed analysis
        if detailed:
            self.show_detailed_analysis(matched_questions, df)
        
        # Check existing AI questions
        existing_ai_questions = AIGeneratedQuestion.objects.filter(
            original_question_id__in=df['question_id'].tolist()
        ).count()
        
        self.stdout.write(f'\n🤖 Existing AI Questions: {existing_ai_questions}')
        
        if existing_ai_questions > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Warning: {existing_ai_questions} AI questions already exist for these question IDs'
                )
            )
        
        # Research readiness assessment
        self.assess_research_readiness(matched_questions, unmatched_questions, missing_source_material)
    
    def show_detailed_analysis(self, matched_questions, df):
        """Show detailed question-by-question analysis"""
        self.stdout.write(f'\n📝 Detailed Analysis (first 5 questions):')
        
        for i, match in enumerate(matched_questions[:5]):
            csv_row = match['csv_row']
            expert_q = match['expert_question']
            
            self.stdout.write(f'\n--- Question {i+1}: {csv_row["question_id"]} ---')
            self.stdout.write(f'Domain: CSV="{csv_row["domain"]}" | DB="{expert_q.domain}"')
            self.stdout.write(f'Type: CSV="{csv_row["question_type"]}" | DB="{expert_q.question_type}"')
            self.stdout.write(f'CSV Source Length: {len(str(csv_row["source_material"]))}')
            self.stdout.write(f'DB Source Length: {len(expert_q.source_material or "")}')
            self.stdout.write(f'CSV Question: {str(csv_row["target_question"])[:100]}...')
            self.stdout.write(f'DB Question: {expert_q.question_text[:100]}...')
            
            # Check for discrepancies
            discrepancies = []
            if csv_row["domain"] != expert_q.domain:
                discrepancies.append("Domain mismatch")
            if csv_row["question_type"] != expert_q.question_type:
                discrepancies.append("Type mismatch")
            
            if discrepancies:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Issues: {", ".join(discrepancies)}')
                )
            else:
                self.stdout.write(self.style.SUCCESS('✅ All fields match'))
    
    def assess_research_readiness(self, matched_questions, unmatched_questions, missing_source_material):
        """Assess if the dataset is ready for research"""
        self.stdout.write(f'\n🎯 Research Readiness Assessment:')
        
        total_questions = len(matched_questions) + len(unmatched_questions)
        usable_questions = len([m for m in matched_questions if m['has_source_material']])
        
        readiness_score = (usable_questions / total_questions * 100) if total_questions > 0 else 0
        
        self.stdout.write(f'Total Questions: {total_questions}')
        self.stdout.write(f'Usable Questions: {usable_questions}')
        self.stdout.write(f'Readiness Score: {readiness_score:.1f}%')
        
        if readiness_score >= 95:
            self.stdout.write(self.style.SUCCESS('🟢 EXCELLENT - Ready for batch processing'))
        elif readiness_score >= 85:
            self.stdout.write(self.style.SUCCESS('🟡 GOOD - Minor issues, but ready to proceed'))
        elif readiness_score >= 70:
            self.stdout.write(self.style.WARNING('🟠 FAIR - Some issues need attention'))
        else:
            self.stdout.write(self.style.ERROR('🔴 POOR - Significant issues must be resolved'))
        
        # Recommendations
        self.stdout.write(f'\n💡 Recommendations:')
        
        if len(unmatched_questions) > 0:
            self.stdout.write(f'• Fix {len(unmatched_questions)} unmatched question IDs')
        
        if len(missing_source_material) > 0:
            self.stdout.write(f'• Add source material for {len(missing_source_material)} questions')
        
        if readiness_score >= 85:
            self.stdout.write('• Proceed with batch generation')
            self.stdout.write(f'• Expected successful generations: ~{usable_questions} questions')


# courses/management/commands/analyze_research_dataset.py

from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
from courses.models import ExpertQuestion, AIGeneratedQuestion

class Command(BaseCommand):
    help = 'Analyze the complete research dataset for comparison study'

    def add_arguments(self, parser):
        parser.add_argument(
            '--export-comparison',
            action='store_true',
            help='Export paired data for research analysis'
        )

    def handle(self, *args, **options):
        export_comparison = options['export_comparison']
        
        self.stdout.write('📊 Research Dataset Analysis\n')
        
        # Expert Questions Analysis
        total_expert = ExpertQuestion.objects.count()
        selected_expert = ExpertQuestion.objects.filter(is_selected_for_research=True).count()
        
        self.stdout.write(f'🎓 Expert Questions:')
        self.stdout.write(f'  Total in database: {total_expert}')
        self.stdout.write(f'  Selected for research: {selected_expert}')
        
        # AI Generated Questions Analysis
        total_ai = AIGeneratedQuestion.objects.count()
        completed_ai = AIGeneratedQuestion.objects.filter(generation_status='completed').count()
        
        self.stdout.write(f'\n🤖 AI Generated Questions:')
        self.stdout.write(f'  Total generated: {total_ai}')
        self.stdout.write(f'  Successfully completed: {completed_ai}')
        
        # Pairing Analysis
        paired_questions = AIGeneratedQuestion.objects.filter(
            generation_status='completed',
            expert_question__isnull=False
        ).count()
        
        self.stdout.write(f'\n🔗 Question Pairing:')
        self.stdout.write(f'  Successfully paired: {paired_questions}')
        self.stdout.write(f'  Ready for comparison: {paired_questions}')
        
        # Domain Distribution
        self.stdout.write(f'\n📚 Domain Distribution:')
        
        domain_analysis = AIGeneratedQuestion.objects.filter(
            generation_status='completed'
        ).values('domain').annotate(
            ai_count=Count('id')
        ).order_by('-ai_count')
        
        for domain in domain_analysis:
            expert_count = ExpertQuestion.objects.filter(
                domain=domain['domain'],
                is_selected_for_research=True
            ).count()
            
            self.stdout.write(f'  {domain["domain"]}:')
            self.stdout.write(f'    Expert: {expert_count}, AI: {domain["ai_count"]}')
        
        # Question Type Distribution
        self.stdout.write(f'\n❓ Question Type Distribution:')
        
        type_analysis = AIGeneratedQuestion.objects.filter(
            generation_status='completed'
        ).values('question_type').annotate(
            ai_count=Count('id')
        ).order_by('-ai_count')
        
        for qtype in type_analysis:
            expert_count = ExpertQuestion.objects.filter(
                question_type=qtype['question_type'],
                is_selected_for_research=True
            ).count()
            
            self.stdout.write(f'  {qtype["question_type"]}:')
            self.stdout.write(f'    Expert: {expert_count}, AI: {qtype["ai_count"]}')
        
        # Quality Metrics
        avg_quality = AIGeneratedQuestion.objects.filter(
            generation_status='completed',
            quality_score__isnull=False
        ).aggregate(avg=Avg('quality_score'))['avg']
        
        if avg_quality:
            self.stdout.write(f'\n⭐ Average AI Quality Score: {avg_quality:.3f}')
        
        # Research Readiness
        if paired_questions >= 180:  # 90% of target 200
            self.stdout.write(self.style.SUCCESS('\n🟢 READY FOR RESEARCH COMPARISON'))
            self.stdout.write(f'Dataset contains {paired_questions} paired questions for analysis')
        else:
            needed = 200 - paired_questions
            self.stdout.write(self.style.WARNING(f'\n🟡 NEEDS MORE DATA'))
            self.stdout.write(f'Need {needed} more paired questions for robust comparison')
        
        # Export comparison data
        if export_comparison:
            self.export_research_data(paired_questions)
    
    def export_research_data(self, paired_count):
        """Export paired data for research analysis"""
        import csv
        from django.utils import timezone
        
        filename = f'research_comparison_data_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # Get paired questions
        paired_questions = AIGeneratedQuestion.objects.filter(
            generation_status='completed',
            expert_question__isnull=False
        ).select_related('expert_question')
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'question_id', 'domain', 'question_type',
                'expert_question_text', 'ai_question_text',
                'source_material_preview', 'ai_quality_score',
                'expert_difficulty', 'generation_date'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for ai_q in paired_questions:
                writer.writerow({
                    'question_id': ai_q.original_question_id,
                    'domain': ai_q.domain,
                    'question_type': ai_q.question_type,
                    'expert_question_text': ai_q.expert_question.question_text,
                    'ai_question_text': ai_q.generated_question_text,
                    'source_material_preview': ai_q.source_material[:500] + '...' if len(ai_q.source_material) > 500 else ai_q.source_material,
                    'ai_quality_score': ai_q.quality_score,
                    'expert_difficulty': ai_q.expert_question.difficulty_level,
                    'generation_date': ai_q.generation_timestamp,
                })
        
        self.stdout.write(
            self.style.SUCCESS(f'📁 Research data exported to: {filename}')
        )
        self.stdout.write(f'Contains {paired_count} paired questions for analysis')