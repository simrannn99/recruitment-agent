"""
Vector search views for semantic candidate and job matching.
"""
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from typing import List, Dict, Optional

from recruitment.models import Candidate, JobPosting
from recruitment.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def _vector_search_candidates(
    query_embedding: List[float],
    limit: int = 10,
    similarity_threshold: float = 0.0
) -> List[Dict]:
    """
    Perform vector similarity search on candidates.
    
    Args:
        query_embedding: The query vector
        limit: Maximum number of results
        similarity_threshold: Minimum similarity score (0-1)
        
    Returns:
        List of candidates with similarity scores
    """
    # Convert to list if numpy array
    if hasattr(query_embedding, 'tolist'):
        query_embedding = query_embedding.tolist()
    
    # Use raw SQL for vector similarity search with pgvector
    # <=> is the cosine distance operator in pgvector
    # 1 - distance = similarity score
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id,
                name,
                email,
                resume_file,
                created_at,
                embedding_generated_at,
                1 - (resume_embedding <=> %s::vector) AS similarity_score
            FROM recruitment_candidate
            WHERE resume_embedding IS NOT NULL
            AND 1 - (resume_embedding <=> %s::vector) >= %s
            ORDER BY resume_embedding <=> %s::vector
            LIMIT %s
        """, [query_embedding, query_embedding, similarity_threshold, query_embedding, limit])
        
        columns = [col[0] for col in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            # Convert datetime to ISO format
            if result.get('created_at'):
                result['created_at'] = result['created_at'].isoformat()
            if result.get('embedding_generated_at'):
                result['embedding_generated_at'] = result['embedding_generated_at'].isoformat()
            results.append(result)
    
    return results


def _vector_search_jobs(
    query_embedding: List[float],
    limit: int = 10,
    similarity_threshold: float = 0.0
) -> List[Dict]:
    """
    Perform vector similarity search on job postings.
    
    Args:
        query_embedding: The query vector
        limit: Maximum number of results
        similarity_threshold: Minimum similarity score (0-1)
        
    Returns:
        List of jobs with similarity scores
    """
    # Convert to list if numpy array
    if hasattr(query_embedding, 'tolist'):
        query_embedding = query_embedding.tolist()
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id,
                title,
                description,
                created_at,
                embedding_generated_at,
                1 - (description_embedding <=> %s::vector) AS similarity_score
            FROM recruitment_jobposting
            WHERE description_embedding IS NOT NULL
            AND 1 - (description_embedding <=> %s::vector) >= %s
            ORDER BY description_embedding <=> %s::vector
            LIMIT %s
        """, [query_embedding, query_embedding, similarity_threshold, query_embedding, limit])
        
        columns = [col[0] for col in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            # Truncate description for response
            if result.get('description') and len(result['description']) > 200:
                result['description'] = result['description'][:200] + '...'
            # Convert datetime to ISO format
            if result.get('created_at'):
                result['created_at'] = result['created_at'].isoformat()
            if result.get('embedding_generated_at'):
                result['embedding_generated_at'] = result['embedding_generated_at'].isoformat()
            results.append(result)
    
    return results


@api_view(['POST'])
def search_candidates_for_job(request):
    """
    Find candidates matching a job posting using semantic search.
    
    Request body:
        {
            "job_id": 1,  // Optional: Use existing job's embedding
            "query_text": "Looking for Python developer...",  // Optional: Generate embedding from text
            "limit": 10,  // Optional: Number of results (default: 10)
            "similarity_threshold": 0.7  // Optional: Minimum similarity (default: 0.0)
        }
    
    Response:
        {
            "query": {"job_id": 1, "title": "Senior Python Developer"},
            "results": [
                {
                    "id": 1,
                    "name": "Alice Chen",
                    "email": "alice@example.com",
                    "similarity_score": 0.92,
                    ...
                }
            ],
            "count": 10
        }
    """
    try:
        job_id = request.data.get('job_id')
        query_text = request.data.get('query_text')
        limit = request.data.get('limit', 10)
        similarity_threshold = request.data.get('similarity_threshold', 0.0)
        
        # Validate inputs
        if not job_id and not query_text:
            return Response(
                {'error': 'Either job_id or query_text must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get query embedding
        query_embedding = None
        query_info = {}
        
        if job_id:
            try:
                job = JobPosting.objects.get(id=job_id)
                if not job.has_embedding:
                    return Response(
                        {'error': f'Job {job_id} does not have an embedding yet. Please wait for embedding generation.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                query_embedding = job.description_embedding
                query_info = {'job_id': job.id, 'title': job.title}
            except JobPosting.DoesNotExist:
                return Response(
                    {'error': f'Job {job_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Generate embedding from query text
            embedding_service = EmbeddingService()
            query_embedding = embedding_service.generate_embedding(query_text)
            query_info = {'query_text': query_text[:100]}
        
        # Perform vector search
        results = _vector_search_candidates(query_embedding, limit, similarity_threshold)
        
        return Response({
            'query': query_info,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error in search_candidates_for_job: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def search_jobs_for_candidate(request):
    """
    Find jobs matching a candidate's resume using semantic search.
    
    Request body:
        {
            "candidate_id": 1,  // Optional: Use existing candidate's embedding
            "query_text": "Python developer with 5 years...",  // Optional: Generate embedding from text
            "limit": 10,  // Optional: Number of results (default: 10)
            "similarity_threshold": 0.7  // Optional: Minimum similarity (default: 0.0)
        }
    
    Response:
        {
            "query": {"candidate_id": 1, "name": "Alice Chen"},
            "results": [
                {
                    "id": 1,
                    "title": "Senior Python Developer",
                    "similarity_score": 0.89,
                    ...
                }
            ],
            "count": 5
        }
    """
    try:
        candidate_id = request.data.get('candidate_id')
        query_text = request.data.get('query_text')
        limit = request.data.get('limit', 10)
        similarity_threshold = request.data.get('similarity_threshold', 0.0)
        
        # Validate inputs
        if not candidate_id and not query_text:
            return Response(
                {'error': 'Either candidate_id or query_text must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get query embedding
        query_embedding = None
        query_info = {}
        
        if candidate_id:
            try:
                candidate = Candidate.objects.get(id=candidate_id)
                if not candidate.has_embedding:
                    return Response(
                        {'error': f'Candidate {candidate_id} does not have an embedding yet. Please wait for embedding generation.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                query_embedding = candidate.resume_embedding
                query_info = {'candidate_id': candidate.id, 'name': candidate.name}
            except Candidate.DoesNotExist:
                return Response(
                    {'error': f'Candidate {candidate_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Generate embedding from query text
            embedding_service = EmbeddingService()
            query_embedding = embedding_service.generate_embedding(query_text)
            query_info = {'query_text': query_text[:100]}
        
        # Perform vector search
        results = _vector_search_jobs(query_embedding, limit, similarity_threshold)
        
        return Response({
            'query': query_info,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error in search_jobs_for_candidate: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def search_similar_candidates(request):
    """
    Find candidates similar to a given candidate (for talent pool building).
    
    Request body:
        {
            "candidate_id": 1,
            "limit": 10,  // Optional: Number of results (default: 10)
            "similarity_threshold": 0.7  // Optional: Minimum similarity (default: 0.0)
        }
    
    Response:
        {
            "query": {"candidate_id": 1, "name": "Alice Chen"},
            "results": [
                {
                    "id": 2,
                    "name": "Bob Smith",
                    "similarity_score": 0.91,
                    ...
                }
            ],
            "count": 10
        }
    """
    try:
        candidate_id = request.data.get('candidate_id')
        limit = request.data.get('limit', 10)
        similarity_threshold = request.data.get('similarity_threshold', 0.0)
        
        if not candidate_id:
            return Response(
                {'error': 'candidate_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            candidate = Candidate.objects.get(id=candidate_id)
            if not candidate.has_embedding:
                return Response(
                    {'error': f'Candidate {candidate_id} does not have an embedding yet.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Candidate.DoesNotExist:
            return Response(
                {'error': f'Candidate {candidate_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Perform vector search (excluding the query candidate itself)
        all_results = _vector_search_candidates(
            candidate.resume_embedding,
            limit + 1,  # Get one extra to account for excluding self
            similarity_threshold
        )
        
        # Filter out the query candidate
        results = [r for r in all_results if r['id'] != candidate_id][:limit]
        
        return Response({
            'query': {'candidate_id': candidate.id, 'name': candidate.name},
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error in search_similar_candidates: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
