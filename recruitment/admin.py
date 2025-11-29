from django.contrib import admin
from django.utils.html import format_html
from recruitment.models import JobPosting, Candidate, Application


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    """Admin interface for JobPosting model."""
    list_display = ['title', 'created_at', 'application_count', 'embedding_status']
    list_filter = ['created_at', 'embedding_generated_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'embedding_generated_at']
    actions = ['batch_analyze_job_applications', 'find_matching_candidates', 'regenerate_embeddings']
    
    def application_count(self, obj):
        """Display number of applications for this job."""
        count = obj.applications.count()
        return format_html('<strong>{}</strong>', count)
    application_count.short_description = 'Applications'
    
    def embedding_status(self, obj):
        """Display embedding generation status."""
        if obj.has_embedding:
            return format_html('<span style="color: green;">✓ Generated</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Pending</span>')
    embedding_status.short_description = 'Embedding'
    
    def batch_analyze_job_applications(self, request, queryset):
        """Admin action to batch analyze all pending applications for selected jobs."""
        from recruitment.tasks import batch_analyze_applications
        
        count = 0
        for job in queryset:
            batch_analyze_applications.delay(job.id)
            count += 1
        
        self.message_user(
            request,
            f"Queued batch analysis for {count} job(s). Check Flower for progress."
        )
    batch_analyze_job_applications.short_description = "Batch analyze all pending applications"
    
    def find_matching_candidates(self, request, queryset):
        """Admin action to find matching candidates for selected jobs."""
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one job posting.", level='WARNING')
            return
        
        job = queryset.first()
        if not job.has_embedding:
            self.message_user(request, f"Job '{job.title}' does not have an embedding yet. Please wait.", level='WARNING')
            return
        
        # Import here to avoid circular imports
        from recruitment.views.search_views import _vector_search_candidates
        
        results = _vector_search_candidates(job.description_embedding, limit=20, similarity_threshold=0.5)
        
        if results:
            message = f"Top {len(results)} matching candidates for '{job.title}':\n"
            for i, candidate in enumerate(results[:5], 1):
                message += f"{i}. {candidate['name']} ({candidate['email']}) - {candidate['similarity_score']:.2%} match\n"
            if len(results) > 5:
                message += f"... and {len(results) - 5} more"
            self.message_user(request, message)
        else:
            self.message_user(request, f"No matching candidates found for '{job.title}'.", level='WARNING')
    find_matching_candidates.short_description = "Find matching candidates for job"
    
    def regenerate_embeddings(self, request, queryset):
        """Admin action to regenerate embeddings for selected jobs."""
        from recruitment.tasks import generate_job_embedding_async
        
        count = 0
        for job in queryset:
            generate_job_embedding_async.delay(job.id)
            count += 1
        
        self.message_user(request, f"Queued embedding generation for {count} job(s).")
    regenerate_embeddings.short_description = "Regenerate embeddings"


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    """Admin interface for Candidate model."""
    list_display = ['name', 'email', 'created_at', 'application_count', 'embedding_status']
    list_filter = ['created_at', 'embedding_generated_at']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at', 'embedding_generated_at', 'resume_text_cache']
    actions = ['find_similar_candidates', 'regenerate_embeddings']
    
    def application_count(self, obj):
        """Display number of applications by this candidate."""
        count = obj.applications.count()
        return format_html('<strong>{}</strong>', count)
    application_count.short_description = 'Applications'
    
    def embedding_status(self, obj):
        """Display embedding generation status."""
        if obj.has_embedding:
            return format_html('<span style="color: green;">✓ Generated</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Pending</span>')
    embedding_status.short_description = 'Embedding'
    
    def find_similar_candidates(self, request, queryset):
        """Admin action to find similar candidates."""
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one candidate.", level='WARNING')
            return
        
        candidate = queryset.first()
        if not candidate.has_embedding:
            self.message_user(request, f"Candidate '{candidate.name}' does not have an embedding yet. Please wait.", level='WARNING')
            return
        
        # Import here to avoid circular imports
        from recruitment.views.search_views import _vector_search_candidates
        
        all_results = _vector_search_candidates(candidate.resume_embedding, limit=11, similarity_threshold=0.5)
        # Filter out the candidate itself
        results = [r for r in all_results if r['id'] != candidate.id][:10]
        
        if results:
            message = f"Top {len(results)} similar candidates to '{candidate.name}':\n"
            for i, similar in enumerate(results[:5], 1):
                message += f"{i}. {similar['name']} ({similar['email']}) - {similar['similarity_score']:.2%} similar\n"
            if len(results) > 5:
                message += f"... and {len(results) - 5} more"
            self.message_user(request, message)
        else:
            self.message_user(request, f"No similar candidates found for '{candidate.name}'.", level='WARNING')
    find_similar_candidates.short_description = "Find similar candidates"
    
    def regenerate_embeddings(self, request, queryset):
        """Admin action to regenerate embeddings for selected candidates."""
        from recruitment.tasks import generate_candidate_embedding_async
        
        count = 0
        for candidate in queryset:
            generate_candidate_embedding_async.delay(candidate.id)
            count += 1
        
        self.message_user(request, f"Queued embedding generation for {count} candidate(s).")
    regenerate_embeddings.short_description = "Regenerate embeddings"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Admin interface for Application model."""
    list_display = [
        'candidate_name',
        'job_title',
        'status',
        'ai_score_display',
        'applied_at'
    ]
    list_filter = ['status', 'applied_at']
    search_fields = [
        'candidate__name',
        'candidate__email',
        'job__title'
    ]
    readonly_fields = [
        'applied_at',
        'updated_at',
        'ai_score',
        'ai_feedback_display'
    ]
    
    fieldsets = (
        ('Application Info', {
            'fields': ('candidate', 'job', 'status')
        }),
        ('AI Analysis', {
            'fields': ('ai_score', 'ai_feedback_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('applied_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'trigger_ai_analysis_async',
        'accept_applications',
        'reject_applications',
        'send_acceptance_emails',
        'send_rejection_emails'
    ]
    
    def candidate_name(self, obj):
        """Display candidate name."""
        return obj.candidate.name
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'
    
    def job_title(self, obj):
        """Display job title."""
        return obj.job.title
    job_title.short_description = 'Job'
    job_title.admin_order_field = 'job__title'
    
    def ai_score_display(self, obj):
        """Display AI score with color coding."""
        if obj.ai_score is None:
            return format_html('<span style="color: gray;">Not analyzed</span>')
        
        # Color code based on score
        if obj.ai_score >= 75:
            color = 'green'
        elif obj.ai_score >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<strong style="color: {};">{}/100</strong>',
            color,
            obj.ai_score
        )
    ai_score_display.short_description = 'AI Score'
    ai_score_display.admin_order_field = 'ai_score'
    
    def ai_feedback_display(self, obj):
        """Display AI feedback in a readable format."""
        if not obj.ai_feedback:
            return "No feedback available"
        
        html = "<div style='line-height: 1.6;'>"
        
        # Summary
        if 'summary' in obj.ai_feedback:
            html += f"<p><strong>Summary:</strong><br>{obj.ai_feedback['summary']}</p>"
        
        # Missing skills
        if 'missing_skills' in obj.ai_feedback and obj.ai_feedback['missing_skills']:
            html += "<p><strong>Missing Skills:</strong><br>"
            html += "<ul>"
            for skill in obj.ai_feedback['missing_skills']:
                html += f"<li>{skill}</li>"
            html += "</ul></p>"
        
        # Interview questions
        if 'interview_questions' in obj.ai_feedback and obj.ai_feedback['interview_questions']:
            html += "<p><strong>Interview Questions:</strong><br>"
            html += "<ol>"
            for question in obj.ai_feedback['interview_questions']:
                html += f"<li>{question}</li>"
            html += "</ol></p>"
        
        html += "</div>"
        return format_html(html)
    ai_feedback_display.short_description = 'AI Feedback'
    
    def trigger_ai_analysis_async(self, request, queryset):
        """Admin action to trigger AI analysis for selected applications (async)."""
        from recruitment.tasks import analyze_application_async
        
        count = 0
        for application in queryset:
            try:
                analyze_application_async.delay(application.id)
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error queuing application {application.id}: {str(e)}",
                    level='ERROR'
                )
        
        if count > 0:
            self.message_user(
                request,
                f"Queued AI analysis for {count} application(s). Check Flower for progress."
            )
    trigger_ai_analysis_async.short_description = "Re-analyze selected applications (async)"
    
    def accept_applications(self, request, queryset):
        """Admin action to accept selected applications."""
        updated = queryset.update(status='accepted')
        self.message_user(request, f"{updated} application(s) marked as accepted.")
    accept_applications.short_description = "Mark selected as Accepted"
    
    def reject_applications(self, request, queryset):
        """Admin action to reject selected applications."""
        updated = queryset.update(status='rejected')
        self.message_user(request, f"{updated} application(s) marked as rejected.")
    reject_applications.short_description = "Mark selected as Rejected"
    
    def send_acceptance_emails(self, request, queryset):
        """Admin action to send acceptance emails for selected applications."""
        from recruitment.tasks import send_application_status_email
        
        count = 0
        for application in queryset.filter(status='accepted'):
            send_application_status_email.delay(application.id, 'accepted')
            count += 1
        
        self.message_user(
            request,
            f"Queued {count} acceptance email(s)."
        )
    send_acceptance_emails.short_description = "Send acceptance emails"
    
    def send_rejection_emails(self, request, queryset):
        """Admin action to send rejection emails for selected applications."""
        from recruitment.tasks import send_application_status_email
        
        count = 0
        for application in queryset.filter(status='rejected'):
            send_application_status_email.delay(application.id, 'rejected')
            count += 1
        
        self.message_user(
            request,
            f"Queued {count} rejection email(s)."
        )
    send_rejection_emails.short_description = "Send rejection emails"
