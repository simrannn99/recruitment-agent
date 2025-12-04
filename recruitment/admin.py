from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from recruitment.models import JobPosting, Candidate, Application
import logging

logger = logging.getLogger(__name__)


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    """Enhanced admin interface for JobPosting model with vector search."""
    list_display = ['title', 'created_at', 'application_count', 'embedding_status']
    list_filter = ['created_at', 'embedding_generated_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'embedding_generated_at', 'matching_candidates_display']
    exclude = ['description_embedding']  # Hide embedding vector from form
    actions = ['test_retriever_agent', 'batch_analyze_job_applications', 'regenerate_embeddings']
    
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
    
    def get_urls(self):
        """Add custom URLs for admin actions."""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:job_id>/test-retriever-sync/',
                self.admin_site.admin_view(self.test_retriever_sync_view),
                name='recruitment_jobposting_test_retriever_sync'
            ),
        ]
        return custom_urls + urls
    
    
    def test_retriever_sync_view(self, request, job_id):
        """Custom view to run RetrieverAgent test synchronously."""
        from django.shortcuts import redirect
        from django.contrib import messages
        from django.urls import reverse
        from django.views.decorators.csrf import csrf_exempt
        import os
        
        try:
            # Get the job
            job = JobPosting.objects.get(id=job_id)
            
            # Import agents
            from app.agents.retriever_agent import RetrieverAgent
            from app.agents.state import AgentState
            from langchain_ollama import ChatOllama
            
            # Initialize LLM
            llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
            
            # Initialize RetrieverAgent
            retriever = RetrieverAgent(llm)
            
            # Create initial state
            initial_state = AgentState(
                job_description=job.description,
                job_id=job.id
            )
            
            # Run retrieval
            logger.info(f"[Admin] Testing RetrieverAgent for job: {job.title}")
            result_state = retriever(initial_state)
            
            # Check for errors
            if result_state.error:
                messages.error(request, f"❌ Retrieval failed: {result_state.error}")
            else:
                # Display results
                candidate_count = len(result_state.retrieved_candidates)
                
                if candidate_count == 0:
                    messages.warning(
                        request,
                        f"⚠️ No matching candidates found for: {job.title}"
                    )
                else:
                    # Show top candidates
                    top_candidates = result_state.retrieved_candidates[:5]
                    
                    messages.success(
                        request,
                        f"✅ RetrieverAgent found {candidate_count} matching candidates for: {job.title}"
                    )
                    
                    for i, candidate in enumerate(top_candidates, 1):
                        match_score = int(candidate.similarity_score * 100)
                        messages.info(
                            request,
                            f"#{i}: {candidate.name} - Match Score: {match_score}/100 "
                            f"(Similarity: {candidate.similarity_score:.1%})"
                        )
                    
                    # Show execution stats
                    if result_state.agent_traces:
                        trace = result_state.agent_traces[-1]
                        tools_used = [tc.tool_name for tc in trace.tools_called]
                        messages.info(
                            request,
                            f"🔧 Tools used: {', '.join(tools_used)} | "
                            f"Execution time: {trace.execution_time_ms}ms"
                        )
        
        except Exception as e:
            logger.error(f"[Admin] RetrieverAgent test failed: {e}")
            messages.error(
                request,
                f"❌ Error testing RetrieverAgent: {str(e)}"
            )
        
        # Redirect back to the job detail page (change view)
        return redirect(reverse('admin:recruitment_jobposting_change', args=[job_id]))
    
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
    
    def test_retriever_agent(self, request, queryset):
        """
        🔍 Test RetrieverAgent: Find matching candidates for selected jobs.
        
        This action demonstrates the RetrieverAgent's ability to:
        - Parse job descriptions
        - Search the database for matching candidates
        - Rank candidates by relevance
        
        Note: This runs synchronously and may take 10-30 seconds.
        """
        from django.contrib import messages
        import os
        
        if queryset.count() > 1:
            messages.warning(request, "⚠️ Please select only ONE job to test the RetrieverAgent")
            return
        
        job = queryset.first()
        
        try:
            # Import agents
            from app.agents.retriever_agent import RetrieverAgent
            from app.agents.state import AgentState
            from langchain_ollama import ChatOllama
            
            # Initialize LLM
            llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
            
            # Initialize RetrieverAgent
            retriever = RetrieverAgent(llm)
            
            # Create initial state (NO candidate specified - triggers retrieval!)
            initial_state = AgentState(
                job_description=job.description,
                job_id=job.id
            )
            
            # Run retrieval
            logger.info(f"[Admin] Testing RetrieverAgent for job: {job.title}")
            result_state = retriever(initial_state)
            
            # Check for errors
            if result_state.error:
                messages.error(request, f"❌ Retrieval failed: {result_state.error}")
                return
            
            # Display results
            candidate_count = len(result_state.retrieved_candidates)
            
            if candidate_count == 0:
                messages.warning(
                    request,
                    f"⚠️ No matching candidates found for: {job.title}"
                )
            else:
                # Show top candidates
                top_candidates = result_state.retrieved_candidates[:5]
                
                messages.success(
                    request,
                    f"✅ RetrieverAgent found {candidate_count} matching candidates for: {job.title}"
                )
                
                for i, candidate in enumerate(top_candidates, 1):
                    # Calculate match score from similarity (0-1 to 0-100)
                    match_score = int(candidate.similarity_score * 100)
                    messages.info(
                        request,
                        f"#{i}: {candidate.name} - Match Score: {match_score}/100 "
                        f"(Similarity: {candidate.similarity_score:.1%})"
                    )
                
                # Show execution stats
                if result_state.agent_traces:
                    trace = result_state.agent_traces[-1]
                    tools_used = [tc.tool_name for tc in trace.tools_called]
                    messages.info(
                        request,
                        f"🔧 Tools used: {', '.join(tools_used)} | "
                        f"Execution time: {trace.execution_time_ms}ms"
                    )
        
        except Exception as e:
            logger.error(f"[Admin] RetrieverAgent test failed: {e}")
            messages.error(
                request,
                f"❌ Error testing RetrieverAgent: {str(e)}"
            )
    
    test_retriever_agent.short_description = "🔍 Test RetrieverAgent (Find Matching Candidates)"


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
        'trigger_multiagent_analysis', 
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
        
        # Check if this is multi-agent analysis
        is_multiagent = 'agent_traces' in obj.ai_feedback or 'detailed_analysis' in obj.ai_feedback
        
        if is_multiagent:
            html += "<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px;'>"
            html += "<strong>🤖 Multi-Agent Analysis Results</strong>"
            html += "</div>"
        
        # Summary
        if 'summary' in obj.ai_feedback:
            html += f"<p><strong>Summary:</strong><br>{obj.ai_feedback['summary']}</p>"
        
        # Multi-dimensional scores 
        if 'detailed_analysis' in obj.ai_feedback:
            analysis = obj.ai_feedback['detailed_analysis']
            html += "<p><strong>📊 Detailed Scores:</strong><br>"
            html += "<ul style='list-style: none; padding-left: 0;'>"
            
            if 'technical_score' in analysis:
                html += f"<li>🔧 Technical: <strong>{analysis['technical_score']}/100</strong></li>"
            if 'experience_score' in analysis:
                html += f"<li>💼 Experience: <strong>{analysis['experience_score']}/100</strong></li>"
            if 'culture_score' in analysis:
                html += f"<li>🤝 Culture Fit: <strong>{analysis['culture_score']}/100</strong></li>"
            
            html += "</ul></p>"
            
            # Strengths
            if 'strengths' in analysis and analysis['strengths']:
                html += "<p><strong>✅ Strengths:</strong><br><ul>"
                for strength in analysis['strengths']:
                    html += f"<li>{strength}</li>"
                html += "</ul></p>"
        
        # Confidence score (NEW)
        if 'confidence_score' in obj.ai_feedback:
            confidence = obj.ai_feedback['confidence_score']
            confidence_pct = f"{confidence * 100:.0f}%"
            color = "green" if confidence >= 0.8 else "orange" if confidence >= 0.6 else "red"
            html += f"<p><strong>🎯 Confidence:</strong> <span style='color: {color}; font-weight: bold;'>{confidence_pct}</span></p>"
        
        # Missing skills
        if 'missing_skills' in obj.ai_feedback and obj.ai_feedback['missing_skills']:
            html += "<p><strong>❌ Missing Skills:</strong><br>"
            html += "<ul>"
            for skill in obj.ai_feedback['missing_skills']:
                html += f"<li>{skill}</li>"
            html += "</ul></p>"
        
        # Interview questions
        if 'interview_questions' in obj.ai_feedback and obj.ai_feedback['interview_questions']:
            html += "<p><strong>❓ Interview Questions:</strong><br>"
            html += "<div style='margin-top: 10px;'>"
            for i, question in enumerate(obj.ai_feedback['interview_questions'], 1):
                # Handle both string and dict formats
                if isinstance(question, str):
                    # Old format: just a string
                    html += f"<div style='background: #3a3a3a; padding: 12px 15px; margin-bottom: 10px; border-left: 4px solid #667eea; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.3);'>"
                    html += f"<strong style='color: #90caf9;'>{i}.</strong> <span style='color: #ffffff;'>{question}</span>"
                    html += "</div>"
                else:
                    # New format: dict with category, difficulty, expected_answer_points
                    question_text = question.get('question', 'No question text')
                    category = question.get('category', 'general')
                    difficulty = question.get('difficulty', 'medium')
                    expected_points = question.get('expected_answer_points', [])
                    
                    # Bright badge colors for dark background
                    category_colors = {
                        'technical': '#2196F3',      # Bright blue
                        'behavioral': '#9C27B0',     # Bright purple
                        'situational': '#FF9800',    # Bright orange
                        'general': '#757575'         # Medium grey
                    }
                    cat_bg = category_colors.get(category.lower(), '#757575')
                    
                    # Difficulty badge colors
                    diff_colors = {
                        'easy': '#4CAF50',      # Bright green
                        'medium': '#FF9800',    # Bright orange
                        'hard': '#F44336'       # Bright red
                    }
                    diff_bg = diff_colors.get(difficulty.lower(), '#757575')
                    
                    html += f"<div style='background: #3a3a3a; padding: 15px; margin-bottom: 12px; border-left: 4px solid {cat_bg}; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);'>"
                    
                    # Question header with badges
                    html += "<div style='display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap;'>"
                    html += f"<strong style='color: #90caf9; font-size: 16px;'>{i}.</strong>"
                    html += f"<span style='background: {cat_bg}; color: #ffffff; padding: 4px 12px; border-radius: 14px; font-size: 12px; font-weight: bold; text-transform: uppercase; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>{category}</span>"
                    html += f"<span style='background: {diff_bg}; color: #ffffff; padding: 4px 12px; border-radius: 14px; font-size: 12px; font-weight: bold; text-transform: uppercase; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>{difficulty}</span>"
                    html += "</div>"
                    
                    # Question text
                    html += f"<div style='color: #ffffff; font-size: 14px; line-height: 1.6; margin-bottom: 10px;'>{question_text}</div>"
                    
                    # Expected answer points (if available)
                    if expected_points:
                        html += "<details style='margin-top: 10px; background: #2c2c2c; padding: 10px; border-radius: 6px;' open>"
                        html += "<summary style='cursor: pointer; color: #64B5F6; font-size: 13px; font-weight: 700; margin-bottom: 8px;'>💡 Expected Answer Points</summary>"
                        html += "<ul style='margin: 8px 0 0 20px; padding: 0; list-style-type: disc;'>"
                        for point in expected_points:
                            html += f"<li style='margin-bottom: 6px; color: #ffffff; font-size: 13px; line-height: 1.5;'>{point}</li>"
                        html += "</ul>"
                        html += "</details>"
                    
                    html += "</div>"
            
            html += "</div></p>"
        
        # Agent execution traces (NEW)
        if 'agent_traces' in obj.ai_feedback and obj.ai_feedback['agent_traces']:
            # Deduplicate traces (LangGraph's operator.add can create duplicates)
            seen = set()
            unique_traces = []
            for trace in obj.ai_feedback['agent_traces']:
                # Create unique key based on agent name and execution time
                key = (trace.get('agent_name'), trace.get('execution_time_ms'))
                if key not in seen:
                    seen.add(key)
                    unique_traces.append(trace)
            
            html += "<details style='margin-top: 15px;'>"
            html += "<summary style='cursor: pointer; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 15px; border-radius: 8px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>🔬 Agent Execution Traces (Click to expand)</summary>"
            html += "<div style='margin-top: 10px; padding: 15px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 8px;'>"
            
            # Execution stats
            if 'total_execution_time_ms' in obj.ai_feedback:
                exec_time = obj.ai_feedback['total_execution_time_ms'] / 1000
                html += f"<p style='background: white; padding: 8px 12px; border-radius: 6px; border-left: 4px solid #4CAF50;'><strong style='color: #333;'>⏱️ Total Execution Time:</strong> <span style='color: #2E7D32; font-weight: bold;'>{exec_time:.1f}s</span></p>"
            
            if 'agents_used' in obj.ai_feedback:
                agents = ', '.join(obj.ai_feedback['agents_used'])
                html += f"<p style='background: white; padding: 8px 12px; border-radius: 6px; border-left: 4px solid #2196F3;'><strong style='color: #333;'>🤖 Agents Used:</strong> <span style='color: #1565C0; font-weight: bold;'>{agents}</span></p>"
            
            # Individual traces with different colors for each agent
            html += "<div style='margin-top: 10px;'>"
            agent_colors = {
                'AnalyzerAgent': '#FF6B6B',      # Coral red
                'InterviewerAgent': '#4ECDC4',   # Turquoise
                'RetrieverAgent': '#95E1D3',     # Mint green
            }
            
            for i, trace in enumerate(unique_traces, 1):
                agent_name = trace.get('agent_name', 'Unknown')
                exec_time_ms = trace.get('execution_time_ms', 0)
                reasoning = trace.get('reasoning_preview', 'No reasoning available')
                
                # Get color for this agent type
                border_color = agent_colors.get(agent_name, '#9B59B6')  # Default purple
                
                html += f"<div style='background: white; padding: 12px 15px; margin-bottom: 10px; border-left: 5px solid {border_color}; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.08);'>"
                html += f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>"
                html += f"<strong style='color: {border_color}; font-size: 14px;'>[{i}] {agent_name}</strong>"
                html += f"<span style='background: {border_color}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;'>{exec_time_ms}ms</span>"
                html += "</div>"
                html += f"<div style='color: #555; font-size: 13px; line-height: 1.5;'>{reasoning}</div>"
                html += "</div>"
            
            html += "</div></div></details>"

        # Safety Guardrails Report
        if 'safety_report' in obj.ai_feedback and obj.ai_feedback['safety_report']:
            safety = obj.ai_feedback['safety_report']
            has_issues = safety.get('has_issues', False)
            
            # Determine border color
            border_color = '#e74c3c' if has_issues else '#27ae60'
            icon = '⚠️' if has_issues else '✅'
            
            html += f"""
            <div style='margin-top: 20px; padding: 15px; background: #2c3e50; border-left: 5px solid {border_color}; border-radius: 8px;'>
                <h3 style='color: {border_color}; margin: 0 0 10px 0;'>{icon} Safety Guardrails Report</h3>
                <p style='color: #ecf0f1;'><strong>Summary:</strong> {safety.get('summary', 'No issues detected')}</p>
            """
            
            # PII Findings
            pii_findings = safety.get('pii_findings', [])
            if pii_findings:
                html += f"<div style='margin-top: 10px; padding: 10px; background: #34495e; border-left: 3px solid #e74c3c; border-radius: 4px;'>"
                html += f"<strong style='color: #e74c3c;'>🔒 PII Detected ({len(pii_findings)} entities)</strong><ul style='color: #ecf0f1;'>"
                for pii in pii_findings[:5]:
                    html += f"<li>{pii.get('entity_type', 'UNKNOWN')} (confidence: {pii.get('score', 0):.0%})</li>"
                html += "</ul></div>"
            
            # Bias Findings
            bias_findings = safety.get('bias_findings', [])
            if bias_findings:
                html += f"<div style='margin-top: 10px; padding: 10px; background: #34495e; border-left: 3px solid #f39c12; border-radius: 4px;'>"
                html += f"<strong style='color: #f39c12;'>⚖️ Bias Detected ({len(bias_findings)} issues)</strong><ul style='color: #ecf0f1;'>"
                for bias in bias_findings[:5]:
                    html += f"<li><strong>{bias.get('category', 'unknown').title()}</strong>: '{bias.get('keyword', '')}' ({bias.get('severity', 'unknown')})</li>"
                html += "</ul></div>"
            
            html += "</div>"
        
        
        html += "</div>"
        return format_html(html)
    ai_feedback_display.short_description = 'AI Feedback'
    
    def trigger_multiagent_analysis(self, request, queryset):
        """
        🤖 Trigger multi-agent AI analysis for selected applications (ASYNC).
        
        Uses the advanced multi-agent orchestration system with:
        - RetrieverAgent (hybrid search)
        - AnalyzerAgent (multi-dimensional scoring)
        - InterviewerAgent (personalized questions)
        
        Runs asynchronously with real-time WebSocket progress updates.
        """
        from recruitment.tasks_multiagent import analyze_application_multiagent
        from django.contrib import messages
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        success_count = 0
        error_count = 0
        task_ids = []
        
        for application in queryset:
            try:
                # Check if candidate has resume text
                if not application.candidate.resume_text_cache:
                    messages.warning(
                        request,
                        f"Skipping {application.candidate.name}: No resume text available"
                    )
                    continue
                
                # Queue the async Celery task
                task = analyze_application_multiagent.delay(application.id)
                task_ids.append(task.id)
                success_count += 1
                
                logger.info(f"Queued multi-agent analysis for application {application.id}, task {task.id}")
                
            except Exception as e:
                error_count += 1
                messages.error(
                    request,
                    f"❌ {application.candidate.name}: Failed to queue task - {str(e)}"
                )
        
        # Show success message
        if success_count > 0:
            messages.success(
                request,
                f"🚀 Queued multi-agent analysis for {success_count} application(s)! "
                f"Real-time updates will appear via WebSocket. Check the Applications list for results."
            )
            
            # Redirect to changelist with task IDs for WebSocket monitoring
            changelist_url = reverse('admin:recruitment_application_changelist')
            task_ids_param = ','.join(task_ids)
            return HttpResponseRedirect(f"{changelist_url}#tasks={task_ids_param}")
        
        if error_count > 0:
            messages.warning(
                request,
                f"⚠️ {error_count} application(s) failed to queue"
            )
    
    trigger_multiagent_analysis.short_description = "🤖 Analyze with Multi-Agent System"
    
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

