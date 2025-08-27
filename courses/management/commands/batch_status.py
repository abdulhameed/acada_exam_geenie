from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
from courses.models import AIGeneratedQuestion

class Command(BaseCommand):
    help = 'Check status of all batch processing'

    def handle(self, *args, **options):
        self.stdout.write('📊 Batch Processing Status\n')
        
        # Overall statistics
        total_ai = AIGeneratedQuestion.objects.count()
        completed = AIGeneratedQuestion.objects.filter(generation_status='completed').count()
        failed = AIGeneratedQuestion.objects.filter(generation_status='failed').count()
        
        self.stdout.write(f'🤖 AI Questions Overview:')
        self.stdout.write(f'  Total: {total_ai}')
        self.stdout.write(f'  ✅ Completed: {completed}')
        self.stdout.write(f'  ❌ Failed: {failed}')
        self.stdout.write(f'  📈 Success Rate: {(completed/total_ai*100):.1f}%' if total_ai > 0 else '  📈 Success Rate: N/A')
        
        # Batch breakdown
        batch_stats = AIGeneratedQuestion.objects.values('research_batch').annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(generation_status='completed')),
            failed=Count('id', filter=Q(generation_status='failed'))
        ).order_by('-total')
        
        if batch_stats:
            self.stdout.write(f'\n📦 Batch Breakdown:')
            for batch in batch_stats:
                batch_name = batch['research_batch'] or 'No batch'
                success_rate = (batch['completed'] / batch['total'] * 100) if batch['total'] > 0 else 0
                
                self.stdout.write(f'  {batch_name}:')
                self.stdout.write(f'    Total: {batch["total"]} | Success: {batch["completed"]} | Failed: {batch["failed"]} ({success_rate:.1f}%)')
        
        # Quality metrics
        avg_quality = AIGeneratedQuestion.objects.filter(
            generation_status='completed',
            quality_score__isnull=False
        ).aggregate(avg=Avg('quality_score'))['avg']
        
        if avg_quality:
            self.stdout.write(f'\n⭐ Average Quality Score: {avg_quality:.3f}')
        
        # Recent activity
        recent_questions = AIGeneratedQuestion.objects.order_by('-created_at')[:5]
        
        if recent_questions:
            self.stdout.write(f'\n🕒 Recent Activity:')
            for q in recent_questions:
                status_emoji = '✅' if q.generation_status == 'completed' else '❌'
                self.stdout.write(f'  {status_emoji} {q.original_question_id} ({q.created_at.strftime("%H:%M")})')

