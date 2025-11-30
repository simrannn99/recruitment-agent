from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from recruitment.models import JobPosting, Candidate, Application


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    """Enhanced admin interface for JobPosting model with vector search."""
    list_display = ['title', 'created_at', 'application_count', 'embedding_status']
    list_filter = ['created_at', 'embedding_generated_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'embedding_generated_at', 'matching_candidates_display']
    exclude = ['description_embedding']  # Hide embedding vector from form
    actions = ['batch_analyze_job_applications', 'regenerate_embeddings']
    
    fieldsets = (
        ('Job Information', {
            'fields': ('title', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at', 'embedding_generated_at'),
            'classes': ('collapse',)
        }),
        ('🔍 AI-Powered Candidate Matching', {
            'fields': ('matching_candidates_display',),
            'description': 'Top candidates matching this job based on semantic similarity of skills and experience'
        }),
    )
    
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
    
    def matching_candidates_display(self, obj):
        """Display top matching candidates with clickable links."""
        if not obj.has_embedding:
            return format_html(
                '<div style="padding: 20px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; margin: 15px 0;">'
                '<strong style="font-size: 14px;">⚠ Embedding Generation in Progress</strong><br>'
                '<span style="color: #856404; font-size: 13px;">Please wait a few seconds for the AI to analyze this job posting, then refresh this page to see matching candidates.</span>'
                '</div>'
            )
        
        # Import here to avoid circular imports
        from recruitment.views.search_views import _vector_search_candidates
        
        try:
            results = _vector_search_candidates(obj.description_embedding, limit=10, similarity_threshold=0.4)
            
            if not results:
                return format_html(
                    '<div style="padding: 20px; background: #f8f9fa; border-left: 4px solid #6c757d; border-radius: 4px; margin: 15px 0;">'
                    '<strong style="font-size: 14px;">No Matching Candidates Found</strong><br>'
                    '<span style="color: #6c757d; font-size: 13px;">No candidates meet the 40% similarity threshold for this position.</span>'
                    '</div>'
                )
            
            # Wrap in collapsible details element
            html = '<details style="margin: 15px 0;">'
            html += '<summary style="cursor: pointer; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; font-weight: 600; font-size: 14px; user-select: none; list-style: none; display: flex; align-items: center; justify-content: space-between;">'
            html += f'<span>🎯 Top {len(results)} Matching Candidates (Click to expand)</span>'
            html += '<span style="font-size: 20px;">▼</span>'
            html += '</summary>'
            
            html += '<div style="margin-top: 10px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
            html += '<table style="width: 100%; border-collapse: collapse;">'
            html += '<thead><tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Rank</th>'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Candidate Name</th>'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Email</th>'
            html += '<th style="padding: 12px 15px; text-align: right; font-weight: 600;">Match Score</th>'
            html += '</tr></thead><tbody>'
            
            for i, candidate in enumerate(results, 1):
                candidate_url = reverse('admin:recruitment_candidate_change', args=[candidate['id']])
                score = candidate['similarity_score']
                
                # Color code based on score
                if score >= 0.7:
                    score_color = '#fff'
                    score_bg = 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)'
                    badge_text = 'Excellent Match'
                elif score >= 0.5:
                    score_color = '#000'
                    score_bg = 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                    badge_text = 'Good Match'
                else:
                    score_color = '#000'
                    score_bg = 'linear-gradient(135deg, #e0e0e0 0%, #c0c0c0 100%)'
                    badge_text = 'Potential Match'
                
                row_bg = '#f8f9fa' if i % 2 == 0 else '#ffffff'
                
                html += f'<tr style="background: {row_bg}; border-bottom: 1px solid #e9ecef; transition: background 0.2s;" onmouseover="this.style.background=\'#e3f2fd\'" onmouseout="this.style.background=\'{row_bg}\'">'
                html += f'<td style="padding: 15px;"><strong style="color: #667eea; font-size: 16px;">#{i}</strong></td>'
                html += f'<td style="padding: 15px;"><a href="{candidate_url}" style="text-decoration: none; color: #1976d2; font-weight: 500; font-size: 14px;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{candidate["name"]}</a></td>'
                html += f'<td style="padding: 15px; color: #6c757d; font-size: 13px;">{candidate["email"]}</td>'
                html += f'<td style="padding: 15px; text-align: right;"><span style="background: {score_bg}; color: {score_color}; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 13px; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.15);" title="{badge_text}">{score:.1%}</span></td>'
                html += '</tr>'
            
            html += '</tbody></table></div>'
            html += f'<div style="padding: 10px 15px; background: #f8f9fa; border-radius: 4px; margin-top: 10px; font-size: 12px; color: #6c757d;">Showing top {len(results)} candidates with ≥40% similarity</div>'
            html += '</details>'
            
            return format_html(html)
            
        except Exception as e:
            return format_html(
                '<div style="padding: 20px; background: #f8d7da; border-left: 4px solid #dc3545; border-radius: 4px; margin: 15px 0;">'
                f'<strong style="color: #721c24; font-size: 14px;">Error Loading Matches</strong><br>'
                f'<span style="color: #721c24; font-size: 13px;">{str(e)}</span>'
                '</div>'
            )
    
    matching_candidates_display.short_description = '🎯 Top Matching Candidates'
    
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
    """Enhanced admin interface for Candidate model with vector search."""
    list_display = ['name', 'email', 'created_at', 'application_count', 'embedding_status']
    list_filter = ['created_at', 'embedding_generated_at']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at', 'embedding_generated_at', 'resume_text_cache', 'matching_jobs_display', 'similar_candidates_display']
    exclude = ['resume_embedding']  # Hide embedding vector from form
    actions = ['regenerate_embeddings']
    
    fieldsets = (
        ('Candidate Information', {
            'fields': ('name', 'email', 'resume_file')
        }),
        ('Resume Content', {
            'fields': ('resume_text_cache',),
            'classes': ('collapse',),
            'description': 'Extracted text from resume PDF'
        }),
        ('Metadata', {
            'fields': ('created_at', 'embedding_generated_at'),
            'classes': ('collapse',)
        }),
        ('💼 AI-Powered Job Matching', {
            'fields': ('matching_jobs_display',),
            'description': 'Top job postings matching this candidate\'s skills and experience'
        }),
        ('🔍 AI-Powered Similar Profiles', {
            'fields': ('similar_candidates_display',),
            'description': 'Candidates with similar skills and experience based on semantic analysis'
        }),
    )
    
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
    
    def matching_jobs_display(self, obj):
        """Display top matching job postings with clickable links."""
        if not obj.has_embedding:
            return format_html(
                '<div style="padding: 20px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; margin: 15px 0;">'
                '<strong style="font-size: 14px;">⚠ Embedding Generation in Progress</strong><br>'
                '<span style="color: #856404; font-size: 13px;">Please wait a few seconds for the AI to analyze this candidate\'s resume, then refresh this page to see matching jobs.</span>'
                '</div>'
            )
        
        # Import here to avoid circular imports
        from recruitment.views.search_views import _vector_search_jobs
        
        try:
            results = _vector_search_jobs(obj.resume_embedding, limit=10, similarity_threshold=0.4)
            
            if not results:
                return format_html(
                    '<div style="padding: 20px; background: #f8f9fa; border-left: 4px solid #6c757d; border-radius: 4px; margin: 15px 0;">'
                    '<strong style="font-size: 14px;">No Matching Jobs Found</strong><br>'
                    '<span style="color: #6c757d; font-size: 13px;">No job postings meet the 40% similarity threshold for this candidate.</span>'
                    '</div>'
                )
            
            # Wrap in collapsible details element
            html = '<details style="margin: 15px 0;">'
            html += '<summary style="cursor: pointer; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; font-weight: 600; font-size: 14px; user-select: none; list-style: none; display: flex; align-items: center; justify-content: space-between;">'
            html += f'<span>💼 Top {len(results)} Matching Jobs (Click to expand)</span>'
            html += '<span style="font-size: 20px;">▼</span>'
            html += '</summary>'
            
            html += '<div style="margin-top: 10px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
            html += '<table style="width: 100%; border-collapse: collapse;">'
            html += '<thead><tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Rank</th>'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Job Title</th>'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Description</th>'
            html += '<th style="padding: 12px 15px; text-align: right; font-weight: 600;">Match Score</th>'
            html += '</tr></thead><tbody>'
            
            for i, job in enumerate(results, 1):
                job_url = reverse('admin:recruitment_jobposting_change', args=[job['id']])
                score = job['similarity_score']
                
                # Color code based on score
                if score >= 0.7:
                    score_color = '#fff'
                    score_bg = 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)'
                    badge_text = 'Excellent Match'
                elif score >= 0.5:
                    score_color = '#000'
                    score_bg = 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                    badge_text = 'Good Match'
                else:
                    score_color = '#000'
                    score_bg = 'linear-gradient(135deg, #e0e0e0 0%, #c0c0c0 100%)'
                    badge_text = 'Potential Match'
                
                row_bg = '#f8f9fa' if i % 2 == 0 else '#ffffff'
                
                # Truncate description for display
                description = job.get('description', '')
                if len(description) > 100:
                    description = description[:100] + '...'
                
                html += f'<tr style="background: {row_bg}; border-bottom: 1px solid #e9ecef; transition: background 0.2s;" onmouseover="this.style.background=\'#e3f2fd\'" onmouseout="this.style.background=\'{row_bg}\'">'
                html += f'<td style="padding: 15px;"><strong style="color: #667eea; font-size: 16px;">#{i}</strong></td>'
                html += f'<td style="padding: 15px;"><a href="{job_url}" style="text-decoration: none; color: #1976d2; font-weight: 500; font-size: 14px;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{job["title"]}</a></td>'
                html += f'<td style="padding: 15px; color: #6c757d; font-size: 13px;">{description}</td>'
                html += f'<td style="padding: 15px; text-align: right;"><span style="background: {score_bg}; color: {score_color}; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 13px; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.15);" title="{badge_text}">{score:.1%}</span></td>'
                html += '</tr>'
            
            html += '</tbody></table></div>'
            html += f'<div style="padding: 10px 15px; background: #f8f9fa; border-radius: 4px; margin-top: 10px; font-size: 12px; color: #6c757d;">Showing top {len(results)} jobs with ≥40% similarity</div>'
            html += '</details>'
            
            return format_html(html)
            
        except Exception as e:
            return format_html(
                '<div style="padding: 20px; background: #f8d7da; border-left: 4px solid #dc3545; border-radius: 4px; margin: 15px 0;">'
                f'<strong style="color: #721c24; font-size: 14px;">Error Loading Matches</strong><br>'
                f'<span style="color: #721c24; font-size: 13px;">{str(e)}</span>'
                '</div>'
            )
    
    matching_jobs_display.short_description = '💼 Top Matching Job Postings'
    
    def similar_candidates_display(self, obj):
        """Display similar candidates with clickable links."""
        if not obj.has_embedding:
            return format_html(
                '<div style="padding: 20px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; margin: 15px 0;">'
                '<strong style="font-size: 14px;">⚠ Embedding Generation in Progress</strong><br>'
                '<span style="color: #856404; font-size: 13px;">Please wait a few seconds for the AI to analyze this candidate\'s profile, then refresh this page.</span>'
                '</div>'
            )
        
        # Import here to avoid circular imports
        from recruitment.views.search_views import _vector_search_candidates
        
        try:
            # Search for similar candidates, excluding the current one
            all_results = _vector_search_candidates(obj.resume_embedding, limit=11, similarity_threshold=0.4)
            results = [r for r in all_results if r['id'] != obj.id][:10]
            
            if not results:
                return format_html(
                    '<div style="padding: 20px; background: #f8f9fa; border-left: 4px solid #6c757d; border-radius: 4px; margin: 15px 0;">'
                    '<strong style="font-size: 14px;">No Similar Candidates Found</strong><br>'
                    '<span style="color: #6c757d; font-size: 13px;">No other candidates meet the 40% similarity threshold.</span>'
                    '</div>'
                )
            
            # Wrap in collapsible details element
            html = '<details style="margin: 15px 0;">'
            html += '<summary style="cursor: pointer; padding: 15px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 8px; font-weight: 600; font-size: 14px; user-select: none; list-style: none; display: flex; align-items: center; justify-content: space-between;">'
            html += f'<span>🔍 Top {len(results)} Similar Candidates (Click to expand)</span>'
            html += '<span style="font-size: 20px;">▼</span>'
            html += '</summary>'
            
            html += '<div style="margin-top: 10px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
            html += '<table style="width: 100%; border-collapse: collapse;">'
            html += '<thead><tr style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;">'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Rank</th>'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Candidate Name</th>'
            html += '<th style="padding: 12px 15px; text-align: left; font-weight: 600;">Email</th>'
            html += '<th style="padding: 12px 15px; text-align: right; font-weight: 600;">Similarity</th>'
            html += '</tr></thead><tbody>'
            
            for i, candidate in enumerate(results, 1):
                candidate_url = reverse('admin:recruitment_candidate_change', args=[candidate['id']])
                score = candidate['similarity_score']
                
                # Color code based on score
                if score >= 0.7:
                    score_color = '#fff'
                    score_bg = 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)'
                elif score >= 0.5:
                    score_color = '#000'
                    score_bg = 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                else:
                    score_color = '#000'
                    score_bg = 'linear-gradient(135deg, #e0e0e0 0%, #c0c0c0 100%)'
                
                row_bg = '#f8f9fa' if i % 2 == 0 else '#ffffff'
                
                html += f'<tr style="background: {row_bg}; border-bottom: 1px solid #e9ecef; transition: background 0.2s;" onmouseover="this.style.background=\'#e3f2fd\'" onmouseout="this.style.background=\'{row_bg}\'">'
                html += f'<td style="padding: 15px;"><strong style="color: #f5576c; font-size: 16px;">#{i}</strong></td>'
                html += f'<td style="padding: 15px;"><a href="{candidate_url}" style="text-decoration: none; color: #1976d2; font-weight: 500; font-size: 14px;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{candidate["name"]}</a></td>'
                html += f'<td style="padding: 15px; color: #6c757d; font-size: 13px;">{candidate["email"]}</td>'
                html += f'<td style="padding: 15px; text-align: right;"><span style="background: {score_bg}; color: {score_color}; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 13px; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">{score:.1%}</span></td>'
                html += '</tr>'
            
            html += '</tbody></table></div>'
            html += f'<div style="padding: 10px 15px; background: #f8f9fa; border-radius: 4px; margin-top: 10px; font-size: 12px; color: #6c757d;">Showing top {len(results)} similar candidates with ≥40% similarity</div>'
            html += '</details>'
            
            return format_html(html)
            
        except Exception as e:
            return format_html(
                '<div style="padding: 20px; background: #f8d7da; border-left: 4px solid #dc3545; border-radius: 4px; margin: 15px 0;">'
                f'<strong style="color: #721c24; font-size: 14px;">Error Loading Similar Candidates</strong><br>'
                f'<span style="color: #721c24; font-size: 13px;">{str(e)}</span>'
                '</div>'
            )
    
    similar_candidates_display.short_description = '🎯 Similar Candidate Profiles'
    
    def regenerate_embeddings(self, request, queryset):
        """Admin action to regenerate embeddings for selected candidates."""
        from recruitment.tasks import generate_candidate_embedding_async
        
        count = 0
        for candidate in queryset:
            generate_candidate_embedding_async.delay(candidate.id)
            count += 1
        
        self.message_user(request, f"Queued embedding generation for {count} candidate(s).")
    regenerate_embeddings.short_description = "Regenerate embeddings"


# Keep the existing Application admin as-is
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Admin interface for Application model."""
    list_display = [
        'candidate_name',
        'job_title',
        'status_display',
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
    
    def status_display(self, obj):
        """Display status with color-coded badges."""
        status = obj.status or 'pending'  # Default to pending if NULL
        
        # Color code based on status
        status_colors = {
            'pending': ('#856404', '#fff3cd', '⏳'),
            'accepted': ('#155724', '#d4edda', '✓'),
            'rejected': ('#721c24', '#f8d7da', '✗'),
        }
        
        text_color, bg_color, icon = status_colors.get(status, ('#6c757d', '#f8f9fa', '?'))
        display_text = status.capitalize()
        
        return format_html(
            '<span style="background: {}; color: {}; padding: 4px 12px; border-radius: 12px; font-weight: 500; font-size: 12px; display: inline-block;">{} {}</span>',
            bg_color,
            text_color,
            icon,
            display_text
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
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
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        count = 0
        task_ids = []
        for application in queryset:
            try:
                task = analyze_application_async.delay(application.id)
                task_ids.append(task.id)
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
                f"Queued AI analysis for {count} application(s). Real-time updates enabled."
            )
            
            # Redirect to changelist with task IDs in URL fragment for WebSocket monitoring
            changelist_url = reverse('admin:recruitment_application_changelist')
            # Join multiple task IDs with commas
            task_ids_param = ','.join(task_ids)
            return HttpResponseRedirect(f"{changelist_url}#task={task_ids_param}")
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
    
    def response_add(self, request, obj, post_url_override=None):
        """Override response_add to store task ID for WebSocket monitoring."""
        from django.contrib import messages
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # Get the default response
        response = super().response_add(request, obj, post_url_override)
        
        # If application was just created and has a task ID, add it to messages
        if hasattr(obj, '_analysis_task_id'):
            task_id = obj._analysis_task_id
            
            # Add a custom message with the task ID embedded
            messages.success(
                request,
                f'Application created successfully. AI analysis in progress (Task ID: {task_id})',
                extra_tags=f'task_id:{task_id}'
            )
            
            # If redirecting to changelist, add task ID as URL parameter
            if isinstance(response, HttpResponseRedirect):
                changelist_url = reverse('admin:recruitment_application_changelist')
                if response.url == changelist_url or response.url == '.':
                    # Redirect to changelist with task ID in URL fragment
                    return HttpResponseRedirect(f"{changelist_url}#task={task_id}")
        
        return response

