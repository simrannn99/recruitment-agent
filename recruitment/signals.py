"""
Django signals for automatic AI analysis triggering.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from recruitment.models import Application
from recruitment.services.ai_analyzer import analyze_application

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Application)
def trigger_ai_analysis(sender, instance, created, **kwargs):
    """
    Automatically trigger AI analysis when a new application is created.
    
    Args:
        sender: The model class (Application)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    if created:
        logger.info(f"New application created: {instance.id}. Triggering AI analysis...")
        
        try:
            # Trigger AI analysis asynchronously (in production, use Celery or similar)
            # For now, we'll call it synchronously
            analyze_application(instance.id)
            logger.info(f"AI analysis completed for application {instance.id}")
            
        except Exception as e:
            logger.error(f"Failed to analyze application {instance.id}: {str(e)}")
            # Don't raise the exception to avoid blocking the application creation
            # The analysis can be retried manually if needed
