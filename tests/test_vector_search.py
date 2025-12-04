"""
Test script for vector search implementation.

This script tests:
1. Embedding service initialization
2. Embedding generation
3. Vector search API endpoints
4. Database queries

Run: python scripts/test_vector_search.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_backend.settings')
django.setup()

import requests
import time
from recruitment.models import Candidate, JobPosting
from recruitment.services.embedding_service import EmbeddingService
from recruitment.tasks import generate_candidate_embedding_async, generate_job_embedding_async


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def test_embedding_service():
    """Test 1: Embedding Service Initialization"""
    print_header("TEST 1: Embedding Service")
    
    try:
        service = EmbeddingService()
        print(f"✓ Embedding service initialized")
        print(f"  Provider: {service.provider}")
        print(f"  Model: {service.model_name}")
        print(f"  Dimensions: {service.dimension}")
        
        # Test embedding generation
        test_text = "Python developer with Django and PostgreSQL experience"
        embedding = service.generate_embedding(test_text)
        
        if embedding:
            print(f"\n✓ Generated embedding successfully")
            print(f"  Text: '{test_text}'")
            print(f"  Embedding length: {len(embedding)}")
            print(f"  First 5 values: {embedding[:5]}")
            return True
        else:
            print("✗ Failed to generate embedding")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_database_status():
    """Test 2: Database Status"""
    print_header("TEST 2: Database Status")
    
    try:
        # Check candidates
        total_candidates = Candidate.objects.count()
        candidates_with_embeddings = Candidate.objects.filter(
            resume_embedding__isnull=False
        ).count()
        
        print(f"Candidates:")
        print(f"  Total: {total_candidates}")
        print(f"  With embeddings: {candidates_with_embeddings}")
        print(f"  Without embeddings: {total_candidates - candidates_with_embeddings}")
        
        # Check jobs
        total_jobs = JobPosting.objects.count()
        jobs_with_embeddings = JobPosting.objects.filter(
            description_embedding__isnull=False
        ).count()
        
        print(f"\nJob Postings:")
        print(f"  Total: {total_jobs}")
        print(f"  With embeddings: {jobs_with_embeddings}")
        print(f"  Without embeddings: {total_jobs - jobs_with_embeddings}")
        
        if total_candidates == 0 and total_jobs == 0:
            print("\n⚠ No data in database. Create some candidates and jobs first!")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_embedding_generation():
    """Test 3: Embedding Generation Tasks"""
    print_header("TEST 3: Embedding Generation")
    
    try:
        # Find a candidate without embedding
        candidate = Candidate.objects.filter(resume_embedding__isnull=True).first()
        
        if not candidate:
            print("⚠ All candidates already have embeddings")
            candidate = Candidate.objects.first()
            if not candidate:
                print("✗ No candidates in database")
                return False
        
        print(f"Testing with candidate: {candidate.name}")
        print(f"  Has embedding: {candidate.has_embedding}")
        
        # Queue embedding generation
        print("\nQueuing embedding generation task...")
        task = generate_candidate_embedding_async.delay(candidate.id)
        print(f"✓ Task queued (ID: {task.id})")
        
        # Wait for task to complete
        print("Waiting for task to complete (max 30 seconds)...")
        for i in range(30):
            time.sleep(1)
            task_result = task.state
            if task_result == 'SUCCESS':
                print(f"✓ Task completed successfully!")
                
                # Refresh candidate from database
                candidate.refresh_from_db()
                print(f"  Embedding generated: {candidate.has_embedding}")
                print(f"  Generated at: {candidate.embedding_generated_at}")
                return True
            elif task_result == 'FAILURE':
                print(f"✗ Task failed: {task.info}")
                return False
            
            if i % 5 == 0:
                print(f"  Still waiting... ({i}s)")
        
        print("⚠ Task did not complete within 30 seconds")
        print("  Check Flower dashboard: http://localhost:5555")
        return False
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test 4: API Endpoints"""
    print_header("TEST 4: API Endpoints")
    
    base_url = "http://localhost:8001"
    
    # Check if server is running
    try:
        response = requests.get(f"{base_url}/admin/", timeout=2)
        print(f"✓ Django server is running")
    except requests.exceptions.ConnectionError:
        print(f"✗ Django server not running at {base_url}")
        print("  Start server: python manage.py runserver 8001")
        return False
    
    # Test 1: Search candidates for job
    print("\n--- Test: Search Candidates for Job ---")
    
    job = JobPosting.objects.filter(description_embedding__isnull=False).first()
    if not job:
        print("⚠ No jobs with embeddings. Skipping API test.")
        return False
    
    try:
        response = requests.post(
            f"{base_url}/api/search/candidates/",
            json={
                "job_id": job.id,
                "limit": 5,
                "similarity_threshold": 0.5
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API call successful")
            print(f"  Job: {data['query'].get('title', 'N/A')}")
            print(f"  Results found: {data['count']}")
            
            if data['results']:
                print("\n  Top matches:")
                for i, candidate in enumerate(data['results'][:3], 1):
                    print(f"    {i}. {candidate['name']} - {candidate['similarity_score']:.2%} match")
            else:
                print("  No matching candidates found (try lowering similarity_threshold)")
            
            return True
        else:
            print(f"✗ API call failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_search_with_query_text():
    """Test 5: Search with Custom Query Text"""
    print_header("TEST 5: Search with Query Text")
    
    base_url = "http://localhost:8001"
    
    # Check if we have candidates with embeddings
    if Candidate.objects.filter(resume_embedding__isnull=False).count() == 0:
        print("⚠ No candidates with embeddings. Skipping test.")
        return False
    
    try:
        query_text = "Senior Python developer with Django and AWS experience"
        print(f"Query: '{query_text}'")
        
        response = requests.post(
            f"{base_url}/api/search/candidates/",
            json={
                "query_text": query_text,
                "limit": 5
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Search successful")
            print(f"  Results found: {data['count']}")
            
            if data['results']:
                print("\n  Top matches:")
                for i, candidate in enumerate(data['results'][:5], 1):
                    print(f"    {i}. {candidate['name']} ({candidate['email']})")
                    print(f"       Similarity: {candidate['similarity_score']:.2%}")
            
            return True
        else:
            print(f"✗ Search failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_similar_candidates():
    """Test 6: Find Similar Candidates"""
    print_header("TEST 6: Find Similar Candidates")
    
    base_url = "http://localhost:8001"
    
    candidate = Candidate.objects.filter(resume_embedding__isnull=False).first()
    if not candidate:
        print("⚠ No candidates with embeddings. Skipping test.")
        return False
    
    try:
        print(f"Finding candidates similar to: {candidate.name}")
        
        response = requests.post(
            f"{base_url}/api/search/similar-candidates/",
            json={
                "candidate_id": candidate.id,
                "limit": 5
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Search successful")
            print(f"  Similar candidates found: {data['count']}")
            
            if data['results']:
                print("\n  Most similar:")
                for i, similar in enumerate(data['results'][:5], 1):
                    print(f"    {i}. {similar['name']} ({similar['email']})")
                    print(f"       Similarity: {similar['similarity_score']:.2%}")
            
            return True
        else:
            print(f"✗ Search failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  VECTOR SEARCH TEST SUITE")
    print("="*60)
    
    results = {
        "Embedding Service": test_embedding_service(),
        "Database Status": test_database_status(),
        "Embedding Generation": test_embedding_generation(),
        "API Endpoints": test_api_endpoints(),
        "Query Text Search": test_search_with_query_text(),
        "Similar Candidates": test_similar_candidates(),
    }
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Vector search is working correctly.")
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")
        print("\nCommon issues:")
        print("  - Celery worker not running: celery -A recruitment_backend worker -l info --pool=solo")
        print("  - Django server not running: python manage.py runserver 8001")
        print("  - No data in database: Create candidates and jobs via admin")
        print("  - Migration not run: python manage.py migrate")


if __name__ == "__main__":
    main()
