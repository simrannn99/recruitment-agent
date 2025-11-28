"""
Celery tasks for background job processing in the recruitment application.

This module contains asynchronous tasks for:
- AI-powered resume analysis
- Email notifications
- Batch processing of applications
"""
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_application_async(self, application_id):
    """
    Asynchronously analyze a job application using AI.
    
    This task is automatically triggered when a new application is created
    via Django signals. It can also be manually triggered from the admin panel.
    
    Args:
        self: Task instance (when bind=True)
        application_id: ID of the Application to analyze
        
    Returns:
        dict: Analysis results with score and feedback
        
    Raises:
        Retry: If analysis fails, retry up to 3 times with 60-second delay
    """
    try:
        logger.info(f"[Task {self.request.id}] Starting AI analysis for application {application_id}")
        
        # Import here to avoid circular imports
        from recruitment.services.ai_analyzer import analyze_application
        
        # Perform the analysis (calls FastAPI service)
        result = analyze_application(application_id)
        
        logger.info(f"[Task {self.request.id}] Completed AI analysis for application {application_id}")
        return result
        
    except Exception as e:
        logger.error(f"[Task {self.request.id}] Error analyzing application {application_id}: {str(e)}")
        
        # Retry with exponential backoff
        # 1st retry: 60s, 2nd retry: 120s, 3rd retry: 180s
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=e, countdown=countdown)


@shared_task
def send_application_status_email(application_id, status):
    """
    Send email notification when application status changes.
    
    Args:
        application_id: ID of the Application
        status: New status ('accepted' or 'rejected')
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Import here to avoid circular imports
        from recruitment.models import Application
        
        application = Application.objects.select_related(
            'candidate', 'job'
        ).get(id=application_id)
        
        # Prepare email content
        subject = f"Application Update: {application.job.title}"
        
        if status == 'accepted':
            message = f"""
Dear {application.candidate.name},

Congratulations! Your application for the position of {application.job.title} has been accepted.

We were impressed by your qualifications and would like to move forward with the next steps in the hiring process.

Best regards,
Recruitment Team
"""
        else:  # rejected
            message = f"""
Dear {application.candidate.name},

Thank you for your interest in the position of {application.job.title}.

After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs.

We appreciate the time you invested in the application process and wish you the best in your job search.

Best regards,
Recruitment Team
"""
        
        # Send email
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [application.candidate.email],
            fail_silently=False,
        )
        
        logger.info(f"Sent {status} email to {application.candidate.email} for application {application_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email for application {application_id}: {str(e)}")
        raise


@shared_task
def batch_analyze_applications(job_id):
    """
    Analyze all pending applications for a specific job in batch.
    
    This task queues individual analysis tasks for each pending application
    that hasn't been analyzed yet.
    
    Args:
        job_id: ID of the JobPosting
        
    Returns:
        dict: Summary of batch analysis with counts
    """
    try:
        # Import here to avoid circular imports
        from recruitment.models import JobPosting
        
        logger.info(f"Starting batch analysis for job {job_id}")
        
        job = JobPosting.objects.get(id=job_id)
        pending_applications = job.applications.filter(
            status='pending',
            ai_score__isnull=True  # Only analyze applications without scores
        )
        
        results = {
            'job_id': job_id,
            'job_title': job.title,
            'total': pending_applications.count(),
            'queued': 0,
            'failed': 0
        }
        
        # Queue individual analysis tasks
        for application in pending_applications:
            try:
                analyze_application_async.delay(application.id)
                results['queued'] += 1
                logger.info(f"Queued analysis for application {application.id}")
            except Exception as e:
                logger.error(f"Failed to queue application {application.id}: {str(e)}")
                results['failed'] += 1
        
        logger.info(f"Batch analysis completed for job {job_id}: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Batch analysis failed for job {job_id}: {str(e)}")
        raise


@shared_task
def cleanup_old_results():
    """
    Periodic task to clean up old rejected applications.
    
    This task can be scheduled with Celery Beat to run daily.
    It removes rejected applications older than 30 days to keep the database clean.
    
    Returns:
        dict: Summary of cleanup operation
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        from recruitment.models import Application
        
        logger.info("Starting cleanup of old rejected applications")
        
        # Delete applications rejected more than 30 days ago
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = Application.objects.filter(
            status='rejected',
            updated_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"Cleanup completed: deleted {deleted_count} old rejected applications")
        
        return {
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise
