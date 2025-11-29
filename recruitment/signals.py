"""
Django signals for automatic AI analysis triggering.
"""
import logging
from django.db.models.signals import post_save, pre_save
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


@receiver(pre_save, sender=Candidate)
def store_old_candidate_values(sender, instance, **kwargs):
    """
    Store old resume file path before save to detect changes.
    """
    if instance.pk:  # Only for existing instances
        try:
            old_instance = Candidate.objects.get(pk=instance.pk)
            instance._old_resume_file = old_instance.resume_file.name if old_instance.resume_file else None
        except Candidate.DoesNotExist:
            instance._old_resume_file = None
    else:
        instance._old_resume_file = None


@receiver(post_save, sender=Candidate)
def trigger_candidate_embedding_generation(sender, instance, created, **kwargs):
    """
    Automatically generate embedding when a candidate is created or resume file is updated.
    
    Args:
        sender: The model class (Candidate)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    should_generate = False
    
    if created:
        # Always generate for new candidates
        should_generate = True
        logger.info(f"New candidate created: {instance.id}. Queuing embedding generation...")
    else:
        # For updates, check if resume file changed
        old_resume_file = getattr(instance, '_old_resume_file', None)
        current_resume_file = instance.resume_file.name if instance.resume_file else None
        
        if old_resume_file != current_resume_file:
            should_generate = True
            logger.info(f"Candidate {instance.id} resume file changed. Queuing embedding regeneration...")
    
    if should_generate:
        try:
            from recruitment.tasks import generate_candidate_embedding_async
            
            task = generate_candidate_embedding_async.delay(instance.id)
            logger.info(f"Embedding generation queued for candidate {instance.id} (task ID: {task.id})")
            
        except Exception as e:
            logger.error(f"Failed to queue embedding generation for candidate {instance.id}: {str(e)}")


@receiver(pre_save, sender=JobPosting)
def store_old_job_values(sender, instance, **kwargs):
    """
    Store old values before save to detect changes.
    """
    if instance.pk:  # Only for existing instances
        try:
            old_instance = JobPosting.objects.get(pk=instance.pk)
            instance._old_description = old_instance.description
            instance._old_title = old_instance.title
        except JobPosting.DoesNotExist:
            instance._old_description = None
            instance._old_title = None
    else:
        instance._old_description = None
        instance._old_title = None


@receiver(post_save, sender=JobPosting)
def trigger_job_embedding_generation(sender, instance, created, **kwargs):
    """
    Automatically generate embedding when a job posting is created or description/title is updated.
    
    Args:
        sender: The model class (JobPosting)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    should_generate = False
    
    if created:
        # Always generate for new jobs
        should_generate = True
        logger.info(f"New job posting created: {instance.id}. Queuing embedding generation...")
    else:
        # For updates, check if description or title changed
        old_description = getattr(instance, '_old_description', None)
        old_title = getattr(instance, '_old_title', None)
        
        if old_description != instance.description or old_title != instance.title:
            should_generate = True
            logger.info(f"Job posting {instance.id} description/title changed. Queuing embedding regeneration...")
    
    if should_generate:
        try:
            from recruitment.tasks import generate_job_embedding_async
            
            task = generate_job_embedding_async.delay(instance.id)
            logger.info(f"Embedding generation queued for job {instance.id} (task ID: {task.id})")
            
        except Exception as e:
            logger.error(f"Failed to queue embedding generation for job {instance.id}: {str(e)}")



