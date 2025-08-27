# from django.contrib import admin
# from .models import Course, CourseContent

# admin.site.register(Course)
# admin.site.register(CourseContent)
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin
from .models import Course, CourseContent, EnhancedCourseContent, ExpertQuestion, ExpertQuestionDataset, QuestionGenerationTemplate, QuestionTemplate


class QuestionTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'question_type', 'difficulty', 'uploaded_at']
    list_filter = ['course', 'question_type', 'difficulty', 'uploaded_at']
    search_fields = ['title', 'description', 'course__name', 'course__code']
    raw_id_fields = ['course']


class QuestionGenerationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'expert_question_types', 'is_active', 'created_at']
    list_filter = ['course', 'expert_question_types', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'course__name', 'course__code']
    raw_id_fields = ['course', 'created_by']


@admin.register(ExpertQuestionDataset)
class ExpertQuestionDatasetAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'source_type', 
        'questions_count',
        'missing_source_count',
        'completion_percentage',
        'upload_date', 
        'is_active'
    ]
    
    list_filter = ['source_type', 'is_active', 'upload_date']
    search_fields = ['name', 'description']
    readonly_fields = ['upload_date']
    
    def questions_count(self, obj):
        """Total questions in dataset"""
        return obj.questions.count()
    questions_count.short_description = "Total Questions"
    
    def missing_source_count(self, obj):
        """Questions missing source material"""
        missing_count = obj.questions.filter(is_missing_source=True).count()
        total_count = obj.questions.count()
        
        if missing_count > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} missing</span>',
                missing_count
            )
        else:
            return format_html(
                '<span style="color: green;">All have source</span>'
            )
    missing_source_count.short_description = "Missing Source"
    
    def completion_percentage(self, obj):
        """Percentage of questions with source material"""
        total = obj.questions.count()
        if total == 0:
            return "N/A"
        
        with_source = obj.questions.filter(is_missing_source=False).count()
        percentage = (with_source / total) * 100
        
        color = "green" if percentage >= 90 else "orange" if percentage >= 50 else "red"
        
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{percentage:.1f}%</span>')
    completion_percentage.short_description = "Completion %"


class EnhancedCourseContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'content_type', 'uploaded_at']
    list_filter = ['course', 'content_type', 'uploaded_at', 'uploaded_by']
    search_fields = ['title', 'description', 'course__name', 'course__code']
    raw_id_fields = ['course', 'uploaded_by']


@admin.register(ExpertQuestion)
class ExpertQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'question_id', 
        'question_text_preview', 
        'question_type', 
        'domain', 
        'source_status_display',
        'difficulty_level',
        'times_used_as_template',
        'is_selected_for_research',
        'selection_batch',
        'selection_date',
        'created_at'
    ]
    
    list_filter = [
        'is_missing_source',
        'source_recovery_attempted', 
        'question_type', 
        'domain', 
        'difficulty_level',
        'dataset',
        'is_selected_for_research',
        'selection_batch',
        'created_at'
    ]
    
    search_fields = [
        'question_id', 
        'question_text', 
        'domain', 
        'video_title',
        'selection_batch'
    ]
    
    readonly_fields = [
        'question_id', 
        'is_missing_source', 
        'source_status_display',
        'source_recovery_date',
        'created_at'
    ]
    
    fieldsets = (
        ('Question Information', {
            'fields': (
                'dataset',
                'question_id',
                'question_text',
                'question_type',
                'domain',
                'difficulty_level'
            )
        }),
        ('Source Material', {
            'fields': (
                'source_material',
                'source_status_display',
                'is_missing_source',
                'source_recovery_attempted',
                'source_recovery_date'
            ),
            'classes': ('collapse',)
        }),
        ('Media Information', {
            'fields': (
                'video_title',
                'video_youtube_link',
                'video_id',
                'file_source'
            ),
            'classes': ('collapse',)
        }),
        ('Usage & Quality', {
            'fields': (
                'times_used_as_template',
                'quality_rating'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_selected_for_research',
        'unmark_selected_for_research',
        'mark_for_source_recovery',
        'mark_source_recovery_attempted',
        'reset_source_flags'
    ]
    
    def question_text_preview(self, obj):
        """Show preview of question text"""
        preview = obj.question_text[:100] + "..." if len(obj.question_text) > 100 else obj.question_text
        return preview
    question_text_preview.short_description = "Question Preview"
    
    def source_status_display(self, obj):
        """Display source status with colored indicators"""
        if obj.source_material and obj.source_material.strip():
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ Has Source</span>'
            )
        elif obj.source_recovery_attempted:
            return format_html(
                '<span style="color: red; font-weight: bold;">❌ Recovery Failed</span>'
            )
        else:
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠️ Missing Source</span>'
            )
    source_status_display.short_description = "Source Status"
    source_status_display.admin_order_field = 'is_missing_source'
    
    def mark_for_source_recovery(self, request, queryset):
        """Mark selected questions for source recovery"""
        updated = queryset.update(
            source_recovery_attempted=False,
            source_recovery_date=None
        )
        self.message_user(request, f'{updated} questions marked for source recovery.')
    mark_for_source_recovery.short_description = "Mark for source recovery"
    
    def mark_source_recovery_attempted(self, request, queryset):
        """Mark selected questions as recovery attempted"""
        from django.utils import timezone
        updated = queryset.update(
            source_recovery_attempted=True,
            source_recovery_date=timezone.now()
        )
        self.message_user(request, f'{updated} questions marked as recovery attempted.')
    mark_source_recovery_attempted.short_description = "Mark recovery attempted"
    
    def reset_source_flags(self, request, queryset):
        """Reset source recovery flags"""
        updated = queryset.update(
            source_recovery_attempted=False,
            source_recovery_date=None
        )
        self.message_user(request, f'{updated} questions had their source flags reset.')
    reset_source_flags.short_description = "Reset source flags"

    def mark_selected_for_research(self, request, queryset):
        """Mark questions as selected for research"""
        from django.utils import timezone
        
        # Only select questions with source material
        valid_questions = queryset.filter(
            source_material__isnull=False
        ).exclude(source_material='')
        
        updated = valid_questions.update(
            is_selected_for_research=True,
            selection_date=timezone.now(),
            selection_batch='admin_manual_selection'
        )
        
        skipped = queryset.count() - updated
        
        message = f'{updated} questions marked as selected for research.'
        if skipped > 0:
            message += f' {skipped} questions skipped (no source material).'
            
        self.message_user(request, message)
    mark_selected_for_research.short_description = "Mark selected for research"
    
    def unmark_selected_for_research(self, request, queryset):
        """Unmark questions from research selection"""
        updated = queryset.update(
            is_selected_for_research=False,
            selection_date=None,
            selection_batch=''
        )
        self.message_user(request, f'{updated} questions unmarked from research selection.')
    unmark_selected_for_research.short_description = "Unmark research selection"

    def has_source_material(self, obj):
        """Display if question has adequate source material"""
        if not obj.source_material:
            return False
        return len(obj.source_material.strip()) >= 100
    
    has_source_material.boolean = True
    has_source_material.short_description = "Has Source"
    

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'school', 'lecturer', 'created_at']
    list_filter = ['school', 'created_at']
    search_fields = ['name', 'code', 'description']

@admin.register(EnhancedCourseContent)
class EnhancedCourseContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'content_type', 'is_processed', 'processing_status', 'uploaded_at']
    list_filter = ['content_type', 'is_processed', 'processing_status', 'uploaded_at']
    search_fields = ['title', 'course__name']


@admin.register(QuestionGenerationTemplate)
class QuestionGenerationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'use_expert_questions', 'is_active', 'created_at']
    list_filter = ['use_expert_questions', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'course__name']


# admin.site.register(Course)
admin.site.register(CourseContent)
admin.site.register(QuestionTemplate, QuestionTemplateAdmin)
# admin.site.register(QuestionGenerationTemplate, QuestionGenerationTemplateAdmin)
# admin.site.register(ExpertQuestionDataset, ExpertQuestionDatasetAdmin)
# admin.site.register(ExpertQuestion, ExpertQuestionAdmin)
# admin.site.register(EnhancedCourseContent, EnhancedCourseContentAdmin)
