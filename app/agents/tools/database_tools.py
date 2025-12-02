"""
Database query tools for agents.

These tools allow agents to interact with the Django database
to search candidates, retrieve job information, and update application status.
"""

from typing import List, Dict, Any, Optional
import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_backend.settings')
django.setup()

from django.db.models import Q
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)


def search_candidates_by_skills(skills: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for candidates who have specific skills in their resume.
    
    Args:
        skills: Comma-separated list of skills to search for
        limit: Maximum number of candidates to return
        
    Returns:
        List of candidate dictionaries with id, name, email, and resume_text
    """
    from recruitment.models import Candidate
    
    try:
        skill_list = [s.strip() for s in skills.split(',')]
        
        # Build query to search in resume text cache
        query = Q()
        for skill in skill_list:
            query |= Q(resume_text_cache__icontains=skill)
        
        candidates = Candidate.objects.filter(query)[:limit]
        
        results = []
        for candidate in candidates:
            results.append({
                'id': candidate.id,
                'name': candidate.name,
                'email': candidate.email,
                'resume_text': candidate.resume_text_cache or '',
                'has_embedding': candidate.has_embedding
            })
        
        logger.info(f"Found {len(results)} candidates with skills: {skills}")
        return results
        
    except Exception as e:
        logger.error(f"Error searching candidates by skills: {e}")
        return []


def vector_search_candidates(
    job_description: str,
    limit: int = 10,
    min_similarity: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Perform semantic vector search to find candidates similar to job description.
    
    Args:
        job_description: Job description text to match against
        limit: Maximum number of candidates to return
        min_similarity: Minimum cosine similarity threshold (0-1)
        
    Returns:
        List of candidate dictionaries with similarity scores
    """
    from recruitment.models import Candidate
    from recruitment.services.embedding_service import EmbeddingService
    
    try:
        # Generate embedding for job description
        embedding_service = EmbeddingService()
        query_embedding = embedding_service.generate_embedding(job_description)
        
        if not query_embedding:
            logger.warning("Failed to generate embedding for job description")
            return []
        
        # Perform vector search using pgvector
        candidates = Candidate.objects.filter(
            resume_embedding__isnull=False
        ).annotate(
            similarity=1 - (
                Candidate.objects.raw(
                    "SELECT resume_embedding <=> %s as distance FROM recruitment_candidate",
                    [query_embedding]
                )[0].distance
            )
        ).filter(
            similarity__gte=min_similarity
        ).order_by('-similarity')[:limit]
        
        results = []
        for candidate in candidates:
            results.append({
                'id': candidate.id,
                'name': candidate.name,
                'email': candidate.email,
                'resume_text': candidate.resume_text_cache or '',
                'similarity_score': float(candidate.similarity) if hasattr(candidate, 'similarity') else 0.0
            })
        
        logger.info(f"Vector search found {len(results)} candidates")
        return results
        
    except Exception as e:
        logger.error(f"Error in vector search: {e}")
        return []


def get_candidate_by_id(candidate_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific candidate by ID.
    
    Args:
        candidate_id: Candidate ID
        
    Returns:
        Candidate dictionary or None if not found
    """
    from recruitment.models import Candidate
    
    try:
        candidate = Candidate.objects.get(id=candidate_id)
        
        return {
            'id': candidate.id,
            'name': candidate.name,
            'email': candidate.email,
            'resume_text': candidate.resume_text_cache or '',
            'has_embedding': candidate.has_embedding,
            'created_at': candidate.created_at.isoformat()
        }
        
    except Candidate.DoesNotExist:
        logger.warning(f"Candidate {candidate_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving candidate {candidate_id}: {e}")
        return None


def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific job posting by ID.
    
    Args:
        job_id: Job posting ID
        
    Returns:
        Job dictionary or None if not found
    """
    from recruitment.models import JobPosting
    
    try:
        job = JobPosting.objects.get(id=job_id)
        
        return {
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'has_embedding': job.has_embedding,
            'created_at': job.created_at.isoformat()
        }
        
    except JobPosting.DoesNotExist:
        logger.warning(f"Job {job_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {e}")
        return None


def get_candidate_applications(candidate_id: int) -> List[Dict[str, Any]]:
    """
    Get all applications for a specific candidate.
    
    Args:
        candidate_id: Candidate ID
        
    Returns:
        List of application dictionaries
    """
    from recruitment.models import Application
    
    try:
        applications = Application.objects.filter(
            candidate_id=candidate_id
        ).select_related('job')
        
        results = []
        for app in applications:
            results.append({
                'id': app.id,
                'job_title': app.job.title,
                'status': app.status,
                'ai_score': app.ai_score,
                'applied_at': app.applied_at.isoformat()
            })
        
        logger.info(f"Found {len(results)} applications for candidate {candidate_id}")
        return results
        
    except Exception as e:
        logger.error(f"Error retrieving applications for candidate {candidate_id}: {e}")
        return []


def update_application_status(
    application_id: int,
    status: str,
    ai_score: Optional[int] = None,
    ai_feedback: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Update an application's status and AI analysis results.
    
    Args:
        application_id: Application ID
        status: New status ('pending', 'accepted', 'rejected')
        ai_score: Optional AI match score (0-100)
        ai_feedback: Optional AI feedback dictionary
        
    Returns:
        True if successful, False otherwise
    """
    from recruitment.models import Application
    
    try:
        application = Application.objects.get(id=application_id)
        
        application.status = status
        if ai_score is not None:
            application.ai_score = ai_score
        if ai_feedback is not None:
            application.ai_feedback = ai_feedback
        
        application.save()
        
        logger.info(f"Updated application {application_id} to status: {status}")
        return True
        
    except Application.DoesNotExist:
        logger.warning(f"Application {application_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error updating application {application_id}: {e}")
        return False


# Create LangChain Tool instances
search_candidates_tool = Tool(
    name="search_candidates_by_skills",
    description="Search for candidates who have specific skills in their resume. Input should be a comma-separated list of skills.",
    func=lambda skills: search_candidates_by_skills(skills, limit=10)
)

vector_search_tool = Tool(
    name="vector_search_candidates",
    description="Perform semantic search to find candidates similar to a job description. Input should be the job description text.",
    func=lambda job_desc: vector_search_candidates(job_desc, limit=10)
)

get_candidate_tool = Tool(
    name="get_candidate_by_id",
    description="Retrieve detailed information about a specific candidate. Input should be the candidate ID (integer).",
    func=get_candidate_by_id
)

get_job_tool = Tool(
    name="get_job_by_id",
    description="Retrieve detailed information about a specific job posting. Input should be the job ID (integer).",
    func=get_job_by_id
)

get_applications_tool = Tool(
    name="get_candidate_applications",
    description="Get all applications for a specific candidate. Input should be the candidate ID (integer).",
    func=get_candidate_applications
)

update_application_tool = Tool(
    name="update_application_status",
    description="Update an application's status. Input should be a dictionary with 'application_id', 'status', and optionally 'ai_score' and 'ai_feedback'.",
    func=lambda params: update_application_status(**params)
)


# Export all tools
DATABASE_TOOLS = [
    search_candidates_tool,
    vector_search_tool,
    get_candidate_tool,
    get_job_tool,
    get_applications_tool,
    update_application_tool
]
