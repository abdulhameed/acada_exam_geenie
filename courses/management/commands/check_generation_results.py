from django.core.management.base import BaseCommand
from django.db.models import Count, Avg
from courses.models import AIGeneratedQuestion

class Command(BaseCommand):
    help = 'Check results of batch question generation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch',
            type=str,
            help='Specific research batch to check'
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export results to CSV'
        )

    def handle(self, *args, **options):
        batch = options.get('batch')
        export = options.get('export')
        
        # Get query
        queryset = AIGeneratedQuestion.objects.all()
        if batch:
            queryset = queryset.filter(research_batch=batch)
        
        # Statistics
        total = queryset.count()
        completed = queryset.filter(generation_status='completed').count()
        failed = queryset.filter(generation_status='failed').count()
        pending = queryset.filter(generation_status='pending').count()
        
        success_rate = (completed / total * 100) if total > 0 else 0
        
        self.stdout.write(
            self.style.SUCCESS(f'📊 Generation Results {"for batch: " + batch if batch else ""}\n')
        )
        self.stdout.write(f'Total Questions: {total}')
        self.stdout.write(f'✅ Completed: {completed}')
        self.stdout.write(f'❌ Failed: {failed}')
        self.stdout.write(f'⏳ Pending: {pending}')
        self.stdout.write(f'📈 Success Rate: {success_rate:.1f}%\n')
        
        # Domain breakdown
        domain_stats = queryset.values('domain').annotate(
            total=Count('id'),
            completed=Count('id', filter=models.Q(generation_status='completed'))
        ).order_by('-total')
        
        self.stdout.write('📚 Domain Breakdown:')
        for stat in domain_stats:
            domain_success = (stat['completed'] / stat['total'] * 100) if stat['total'] > 0 else 0
            self.stdout.write(
                f"  {stat['domain']}: {stat['completed']}/{stat['total']} ({domain_success:.1f}%)"
            )
        
        # Question type breakdown
        type_stats = queryset.values('question_type').annotate(
            total=Count('id'),
            completed=Count('id', filter=models.Q(generation_status='completed'))
        ).order_by('-total')
        
        self.stdout.write('\n❓ Question Type Breakdown:')
        for stat in type_stats:
            type_success = (stat['completed'] / stat['total'] * 100) if stat['total'] > 0 else 0
            self.stdout.write(
                f"  {stat['question_type']}: {stat['completed']}/{stat['total']} ({type_success:.1f}%)"
            )
        
        # Quality scores
        avg_quality = queryset.filter(
            generation_status='completed',
            quality_score__isnull=False
        ).aggregate(avg_score=Avg('quality_score'))['avg_score']
        
        if avg_quality:
            self.stdout.write(f'\n⭐ Average Quality Score: {avg_quality:.2f}')
        
        # Recent failures
        recent_failures = queryset.filter(
            generation_status='failed'
        ).order_by('-created_at')[:5]
        
        if recent_failures:
            self.stdout.write('\n❌ Recent Failures:')
            for failure in recent_failures:
                self.stdout.write(f'  • {failure.original_question_id}: {failure.error_message[:100]}...')
        
        # Export to CSV if requested
        if export:
            self.export_results(queryset, batch)

    def export_results(self, queryset, batch_name=None):
        """Export results to CSV"""
        import csv
        from django.utils import timezone
        
        filename = f'generation_results_{batch_name or "all"}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'original_question_id', 'domain', 'question_type', 'generation_status',
                'quality_score', 'generated_question_preview', 'error_message',
                'generation_timestamp', 'processing_duration'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for question in queryset:
                writer.writerow({
                    'original_question_id': question.original_question_id,
                    'domain': question.domain,
                    'question_type': question.question_type,
                    'generation_status': question.generation_status,
                    'quality_score': question.quality_score,
                    'generated_question_preview': question.get_truncated_question(200),
                    'error_message': question.error_message,
                    'generation_timestamp': question.generation_timestamp,
                    'processing_duration': question.processing_duration,
                })
        
        self.stdout.write(
            self.style.SUCCESS(f'📁 Results exported to: {filename}')
        )