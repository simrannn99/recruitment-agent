"""
Celery configuration for recruitment_backend project.

This module initializes the Celery application and configures it to work with Django.
"""
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_backend.settings')

# Create Celery application instance
app = Celery('recruitment_backend')

# Load configuration from Django settings with 'CELERY' namespace
# This means all Celery config options must be specified in uppercase
# and prefixed with CELERY_, e.g., CELERY_BROKER_URL
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
# This will look for tasks.py in each app
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    print(f'Request: {self.request!r}')
