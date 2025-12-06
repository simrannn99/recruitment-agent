"""
Custom admin views for recruitment platform.

Provides additional admin functionality beyond standard Django admin.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.conf import settings


@staff_member_required
@require_http_methods(["GET"])
def chat_view(request):
    """
    Custom admin view for AI chat interface.
    
    Provides a conversational interface to interact with the AI recruitment assistant.
    Integrates with FastAPI chat endpoints for session management and message handling.
    """
    context = {
        'title': 'AI Recruitment Assistant',
        'site_title': 'Recruitment Platform',
        'site_header': 'Recruitment Platform Administration',
        'fastapi_url': 'http://localhost:8000/api/ai/chat',
        'has_permission': True,
    }
    return render(request, 'admin/chat.html', context)
