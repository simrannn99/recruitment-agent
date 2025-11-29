"""
Views for serving WebSocket test pages and demos.
"""

from django.shortcuts import render


def websocket_test(request):
    """Serve the WebSocket test page for monitoring Celery tasks."""
    return render(request, 'websocket_test.html')
