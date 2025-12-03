"""
Service layer for AI-powered application analysis.
Integrates with the FastAPI AI service for resume screening.
"""
import requests
import logging
from django.conf import settings

from recruitment.models import Application
from recruitment.utils.pdf_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)

# AI Service Configuration
AI_SERVICE_URL = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8000/analyze')
AI_SERVICE_TIMEOUT = getattr(settings, 'AI_SERVICE_TIMEOUT', 120)  # 2 minutes timeout


def analyze_application(application_id):
    """
    Analyze a job application using the AI service.
    
    This function:
    1. Retrieves the application, job description, and candidate resume
    2. Extracts text from the PDF resume
    3. Sends a request to the FastAPI AI service
    4. Updates the application with AI score and feedback
    
    Args:
        application_id (int): ID of the Application to analyze
        
    Returns:
        dict: Analysis results containing score and feedback
        
    Raises:
        Application.DoesNotExist: If application not found
        requests.RequestException: If AI service call fails
    """
    try:
        # 1. Retrieve the application
        application = Application.objects.select_related('job', 'candidate').get(id=application_id)
        
        logger.info(f"Analyzing application {application_id}: {application.candidate.name} -> {application.job.title}")
        
        # 2. Get job description
        job_description = application.job.description
        
        # 3. Extract resume text from PDF
        # Handle case where no resume file is uploaded
        if application.candidate.resume_file:
            resume_file_path = application.candidate.resume_file.path
        else:
            resume_file_path = None
        
        resume_text = extract_text_from_pdf(resume_file_path)
        
        logger.debug(f"Extracted {len(resume_text)} characters from resume")
        
        # 4. Prepare request payload
        payload = {
            "job_description": job_description,
            "resume_text": resume_text
        }
        
        # 5. Call AI service
        logger.info(f"Calling AI service at {AI_SERVICE_URL}")
        response = requests.post(
            AI_SERVICE_URL,
            json=payload,
            timeout=AI_SERVICE_TIMEOUT
        )
        
        # 6. Check response
        response.raise_for_status()
        ai_result = response.json()
        
        logger.info(f"AI analysis complete. Score: {ai_result.get('match_score')}")
        
        # 7. Update application with AI results (including safety report)
        application.ai_score = ai_result.get('match_score')
        application.ai_feedback = {
            'summary': ai_result.get('summary'),
            'missing_skills': ai_result.get('missing_skills', []),
            'interview_questions': ai_result.get('interview_questions', []),
            'safety_report': ai_result.get('safety_report')  # Include safety guardrails report
        }
        application.save()
        
        logger.info(f"Application {application_id} updated with AI analysis")
        
        return {
            'success': True,
            'application_id': application_id,
            'score': application.ai_score,
            'feedback': application.ai_feedback
        }
        
    except Application.DoesNotExist:
        logger.error(f"Application {application_id} not found")
        raise
        
    except requests.RequestException as e:
        logger.error(f"AI service request failed: {str(e)}")
        # Update application to indicate analysis failed
        try:
            application = Application.objects.get(id=application_id)
            application.ai_feedback = {
                'error': f"AI analysis failed: {str(e)}"
            }
            application.save()
        except:
            pass
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error analyzing application {application_id}: {str(e)}")
        raise


def bulk_analyze_applications(application_ids):
    """
    Analyze multiple applications in bulk.
    
    Args:
        application_ids (list): List of application IDs to analyze
        
    Returns:
        dict: Results summary with successes and failures
    """
    results = {
        'total': len(application_ids),
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for app_id in application_ids:
        try:
            analyze_application(app_id)
            results['successful'] += 1
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'application_id': app_id,
                'error': str(e)
            })
            logger.error(f"Failed to analyze application {app_id}: {str(e)}")
    
    logger.info(f"Bulk analysis complete: {results['successful']}/{results['total']} successful")
    return results


def reanalyze_application(application_id):
    """
    Re-analyze an existing application (e.g., after job description update).
    
    Args:
        application_id (int): ID of the Application to re-analyze
        
    Returns:
        dict: Analysis results
    """
    logger.info(f"Re-analyzing application {application_id}")
    return analyze_application(application_id)
