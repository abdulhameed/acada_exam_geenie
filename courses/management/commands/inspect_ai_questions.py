from django.core.management.base import BaseCommand
from django.db.models import Q
from courses.models import AIGeneratedQuestion, ExpertQuestion

class Command(BaseCommand):
    help = 'Inspect generated AI questions and compare with expert questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-id',
            type=str,
            help='Specific batch to inspect'
        )
        parser.add_argument(
            '--question-id',
            type=str,
            help='Specific question ID to inspect'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of questions to show (default: 5)'
        )
        parser.add_argument(
            '--show-full-text',
            action='store_true',
            help='Show full question text instead of preview'
        )

    def handle(self, *args, **options):
        batch_id = options.get('batch_id')
        question_id = options.get('question_id')
        limit = options['limit']
        show_full = options['show_full_text']
        
        # Build query
        queryset = AIGeneratedQuestion.objects.select_related('expert_question')
        
        if question_id:
            queryset = queryset.filter(original_question_id=question_id)
        elif batch_id:
            queryset = queryset.filter(research_batch=batch_id)
        else:
            queryset = queryset.order_by('-created_at')
        
        questions = queryset[:limit]
        
        if not questions.exists():
            self.stdout.write(self.style.WARNING('No AI questions found matching criteria'))
            return
        
        self.stdout.write(f'🔍 Inspecting {questions.count()} AI Questions:\n')
        
        for ai_q in questions:
            self.show_question_comparison(ai_q, show_full)
    
    def show_question_comparison(self, ai_question, show_full_text=False):
        """Show side-by-side comparison of expert vs AI question"""
        expert_q = ai_question.expert_question
        
        self.stdout.write(f'{"="*80}')
        self.stdout.write(f'Question ID: {ai_question.original_question_id}')
        self.stdout.write(f'Domain: {ai_question.domain} | Type: {ai_question.question_type}')
        self.stdout.write(f'Quality Score: {ai_question.quality_score or "N/A"}')
        self.stdout.write(f'Generation Time: {ai_question.processing_duration or "N/A"}s')
        self.stdout.write(f'Created: {ai_question.created_at.strftime("%Y-%m-%d %H:%M")}')
        
        if expert_q:
            self.stdout.write(f'\n🎓 EXPERT QUESTION:')
            expert_text = expert_q.question_text if show_full_text else expert_q.question_text[:200] + '...' if len(expert_q.question_text) > 200 else expert_q.question_text
            self.stdout.write(f'{expert_text}')
        
        self.stdout.write(f'\n🤖 AI GENERATED QUESTION:')
        ai_text = ai_question.generated_question_text if show_full_text else ai_question.generated_question_text[:200] + '...' if len(ai_question.generated_question_text) > 200 else ai_question.generated_question_text
        self.stdout.write(f'{ai_text}')
        
        self.stdout.write(f'\n📖 SOURCE MATERIAL PREVIEW:')
        source_preview = ai_question.source_material[:300] + '...' if len(ai_question.source_material) > 300 else ai_question.source_material
        self.stdout.write(f'{source_preview}')
        
        # Quick comparison metrics
        if expert_q:
            expert_length = len(expert_q.question_text)
            ai_length = len(ai_question.generated_question_text)
            length_ratio = ai_length / expert_length if expert_length > 0 else 0
            
            self.stdout.write(f'\n📏 Quick Metrics:')
            self.stdout.write(f'  Expert Length: {expert_length} chars')
            self.stdout.write(f'  AI Length: {ai_length} chars')
            self.stdout.write(f'  Length Ratio: {length_ratio:.2f}')
        
        self.stdout.write(f'\n')
