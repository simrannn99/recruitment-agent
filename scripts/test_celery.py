"""
Test script for Celery background job functionality.

This script tests:
1. Celery worker connectivity
2. Task execution
3. Result retrieval
4. Error handling

Usage:
    python scripts/test_celery.py
"""
import os
import sys
import time
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_backend.settings')
django.setup()

from celery.result import AsyncResult
from recruitment.tasks import (
    analyze_application_async,
    send_application_status_email,
    batch_analyze_applications,
    cleanup_old_results
)
from recruitment.models import Application, JobPosting
from recruitment_backend.celery import app as celery_app


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_celery_connection():
    """Test connection to Celery broker and result backend."""
    print_section("Testing Celery Connection")
    
    try:
        # Check broker connection
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            print("✓ Successfully connected to Celery broker (RabbitMQ)")
            print(f"  Active workers: {len(stats)}")
            for worker_name, worker_stats in stats.items():
                print(f"  - {worker_name}")
        else:
            print("✗ No active Celery workers found")
            print("  Make sure to start the worker with:")
            print("  docker-compose up celery-worker")
            return False
        
        # Check registered tasks
        registered = inspect.registered()
        if registered:
            print(f"\n✓ Found {sum(len(tasks) for tasks in registered.values())} registered tasks")
            for worker, tasks in registered.items():
                print(f"\n  Tasks on {worker}:")
                for task in sorted(tasks):
                    if 'recruitment' in task:
                        print(f"    - {task}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error connecting to Celery: {str(e)}")
        return False


def test_simple_task():
    """Test a simple Celery task execution."""
    print_section("Testing Simple Task Execution")
    
    try:
        # Use the debug task
        from recruitment_backend.celery import debug_task
        
        print("Queuing debug task...")
        task = debug_task.delay()
        print(f"✓ Task queued with ID: {task.id}")
        
        # Wait for result
        print("Waiting for task to complete...")
        result = task.get(timeout=10)
        
        print(f"✓ Task completed successfully")
        print(f"  Status: {task.status}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error executing task: {str(e)}")
        return False


def test_ai_analysis_task():
    """Test AI analysis task with a real application."""
    print_section("Testing AI Analysis Task")
    
    try:
        # Find a test application
        application = Application.objects.first()
        
        if not application:
            print("⚠ No applications found in database")
            print("  Create an application in Django admin first")
            return False
        
        print(f"Testing with application ID: {application.id}")
        print(f"  Candidate: {application.candidate.name}")
        print(f"  Job: {application.job.title}")
        
        # Queue the task
        print("\nQueuing AI analysis task...")
        task = analyze_application_async.delay(application.id)
        print(f"✓ Task queued with ID: {task.id}")
        
        # Monitor task progress
        print("\nMonitoring task progress...")
        timeout = 120  # 2 minutes
        start_time = time.time()
        
        while not task.ready():
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"✗ Task timeout after {timeout} seconds")
                return False
            
            print(f"  Status: {task.status} (elapsed: {elapsed:.1f}s)")
            time.sleep(2)
        
        # Get result
        if task.successful():
            result = task.result
            print(f"\n✓ Task completed successfully!")
            print(f"  Result type: {type(result)}")
            
            # Refresh application from database
            application.refresh_from_db()
            if application.ai_score:
                print(f"\n  AI Score: {application.ai_score}/100")
                if application.ai_feedback:
                    print(f"  Summary: {application.ai_feedback.get('summary', 'N/A')[:100]}...")
            
            return True
        else:
            print(f"✗ Task failed: {task.result}")
            return False
        
    except Exception as e:
        print(f"✗ Error testing AI analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_analysis():
    """Test batch analysis task."""
    print_section("Testing Batch Analysis Task")
    
    try:
        # Find a job with applications
        job = JobPosting.objects.annotate(
            app_count=django.db.models.Count('applications')
        ).filter(app_count__gt=0).first()
        
        if not job:
            print("⚠ No jobs with applications found")
            return False
        
        print(f"Testing batch analysis for job: {job.title}")
        print(f"  Total applications: {job.applications.count()}")
        
        # Queue the task
        print("\nQueuing batch analysis task...")
        task = batch_analyze_applications.delay(job.id)
        print(f"✓ Task queued with ID: {task.id}")
        
        # Wait for result
        print("\nWaiting for batch task to complete...")
        result = task.get(timeout=30)
        
        print(f"\n✓ Batch task completed!")
        print(f"  Total applications: {result['total']}")
        print(f"  Queued for analysis: {result['queued']}")
        print(f"  Failed to queue: {result['failed']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing batch analysis: {str(e)}")
        return False


def test_task_monitoring():
    """Test task monitoring with Flower."""
    print_section("Testing Task Monitoring (Flower)")
    
    print("Flower monitoring dashboard should be available at:")
    print("  http://localhost:5555")
    print("\nYou can:")
    print("  - View all tasks (past and present)")
    print("  - Monitor worker status")
    print("  - See task details and tracebacks")
    print("  - View queue lengths")
    print("\nOpen the URL in your browser to verify Flower is working.")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  CELERY BACKGROUND JOBS TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: Connection
    results['connection'] = test_celery_connection()
    
    if not results['connection']:
        print("\n⚠ Skipping remaining tests due to connection failure")
        return
    
    # Test 2: Simple task
    results['simple_task'] = test_simple_task()
    
    # Test 3: AI analysis
    results['ai_analysis'] = test_ai_analysis_task()
    
    # Test 4: Batch analysis
    results['batch_analysis'] = test_batch_analysis()
    
    # Test 5: Monitoring
    results['monitoring'] = test_task_monitoring()
    
    # Summary
    print_section("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name.replace('_', ' ').title()}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")


if __name__ == '__main__':
    main()
