"""
Django signals for automatic AI analysis triggering.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from recruitment.models import Application

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Application)
def trigger_ai_analysis(sender, instance, created, **kwargs):
    """
    Automatically trigger AI analysis when a new application is created.
    
    This signal queues the analysis as a background task using Celery,
    allowing the HTTP request to return immediately without waiting for
    the AI analysis to complete.
    
    Args:
        sender: The model class (Application)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    if created:
        logger.info(f"New application created: {instance.id}. Queuing AI analysis...")
        
        try:
            # Import here to avoid circular imports
            from recruitment.tasks import analyze_application_async
            
            # Queue task asynchronously with Celery
            task = analyze_application_async.delay(instance.id)
            logger.info(f"AI analysis queued for application {instance.id} (task ID: {task.id})")
            
        except Exception as e:
            logger.error(f"Failed to queue AI analysis for application {instance.id}: {str(e)}")
            # Don't raise the exception to avoid blocking the application creation
