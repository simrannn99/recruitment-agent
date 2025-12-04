"""
Celery configuration for recruitment_backend project.

This module initializes the Celery application and configures it to work with Django.
"""
import os
from celery import Celery
from celery.schedules import crontab

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

# Explicitly import multi-agent tasks (not auto-discovered because it's in tasks_multiagent.py)
app.autodiscover_tasks(['recruitment'], related_name='tasks_multiagent')

# Explicitly import analytics tasks
app.autodiscover_tasks(['recruitment'], related_name='tasks_analytics')

# Configure Celery Beat schedule for automated analytics sync
app.conf.beat_schedule = {
    'analytics-incremental-sync': {
        'task': 'analytics.incremental_sync',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {'queue': 'analytics'}
    },
    'analytics-full-sync': {
        'task': 'analytics.full_sync',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'options': {'queue': 'analytics'}
    },
    'analytics-train-models': {
        'task': 'analytics.train_models',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Weekly on Sunday at 3 AM
        'options': {'queue': 'analytics'}
    },
    'analytics-export-parquet': {
        'task': 'analytics.export_parquet',
        'schedule': crontab(hour=4, minute=0),  # Daily at 4 AM
        'options': {'queue': 'analytics'}
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    print(f'Request: {self.request!r}')
