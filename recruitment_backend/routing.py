"""
WebSocket URL routing configuration for the recruitment application.

This module defines the WebSocket URL patterns that map to consumers.
"""

from django.urls import re_path
from recruitment.consumers import TaskStatusConsumer

websocket_urlpatterns = [
    re_path(r'ws/tasks/(?P<task_id>[\w-]+)/$', TaskStatusConsumer.as_asgi()),
]
