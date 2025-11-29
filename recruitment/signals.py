"""
Django signals for automatic AI analysis triggering.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from recruitment.models import Application, Candidate, JobPosting

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


@receiver(post_save, sender=Candidate)
def trigger_candidate_embedding_generation(sender, instance, created, **kwargs):
    """
    Automatically generate embedding when a candidate is created or resume is updated.
    
    Args:
        sender: The model class (Candidate)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    # Only generate if:
    # 1. New candidate created, OR
    # 2. Resume file changed and no embedding exists yet
    should_generate = created or (not instance.has_embedding and instance.resume_file)
    
    if should_generate:
        logger.info(f"Candidate {'created' if created else 'updated'}: {instance.id}. Queuing embedding generation...")
        
        try:
            from recruitment.tasks import generate_candidate_embedding_async
            
            task = generate_candidate_embedding_async.delay(instance.id)
            logger.info(f"Embedding generation queued for candidate {instance.id} (task ID: {task.id})")
            
        except Exception as e:
            logger.error(f"Failed to queue embedding generation for candidate {instance.id}: {str(e)}")


@receiver(post_save, sender=JobPosting)
def trigger_job_embedding_generation(sender, instance, created, **kwargs):
    """
    Automatically generate embedding when a job posting is created or description is updated.
    
    Args:
        sender: The model class (JobPosting)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    # Only generate if:
    # 1. New job created, OR
    # 2. Description changed and no embedding exists yet
    should_generate = created or not instance.has_embedding
    
    if should_generate:
        logger.info(f"Job posting {'created' if created else 'updated'}: {instance.id}. Queuing embedding generation...")
        
        try:
            from recruitment.tasks import generate_job_embedding_async
            
            task = generate_job_embedding_async.delay(instance.id)
            logger.info(f"Embedding generation queued for job {instance.id} (task ID: {task.id})")
            
        except Exception as e:
            logger.error(f"Failed to queue embedding generation for job {instance.id}: {str(e)}")

