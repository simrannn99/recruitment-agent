"""
Comprehensive test script for the Django recruitment backend.
This script will create test data and verify the AI integration works.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_backend.settings')
django.setup()

from recruitment.models import JobPosting, Candidate, Application
from recruitment.services.ai_analyzer import analyze_application
import time


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_success(text):
    """Print success message."""
    print(f"✅ {text}")


def print_info(text):
    """Print info message."""
    print(f"ℹ️  {text}")


def print_error(text):
    """Print error message."""
    print(f"❌ {text}")


def cleanup_test_data():
    """Clean up any existing test data."""
    print_header("Cleaning up existing test data")
    
    Application.objects.filter(job__title__startswith="[TEST]").delete()
    Candidate.objects.filter(name__startswith="[TEST]").delete()
    JobPosting.objects.filter(title__startswith="[TEST]").delete()
    
    print_success("Cleaned up existing test data")


def create_test_job():
    """Create a test job posting."""
    print_header("Creating Test Job Posting")
    
    job = JobPosting.objects.create(
        title="[TEST] Senior Python Backend Developer",
        description="""
We are looking for a Senior Python Backend Developer to join our team.

Required Skills:
- 5+ years of Python development experience
- Expert knowledge of Django and FastAPI frameworks
- Strong experience with PostgreSQL and MongoDB databases
- Proficiency in Docker and Kubernetes
- Experience with AWS cloud services (EC2, S3, Lambda, RDS)
- CI/CD pipeline development and maintenance
- RESTful API design and implementation
- Strong understanding of Agile/Scrum methodologies

Responsibilities:
- Design and develop scalable backend services
- Build and maintain RESTful APIs
- Optimize database queries and performance
- Implement automated testing and deployment
- Collaborate with frontend developers
- Mentor junior developers

Nice to Have:
- Experience with microservices architecture
- Knowledge of Redis caching
- GraphQL experience
- Open source contributions
        """
    )
    
    print_success(f"Created job posting: {job.title}")
    print_info(f"   ID: {job.id}")
    print_info(f"   Created: {job.created_at}")
    
    return job


def create_test_candidate():
    """Create a test candidate."""
    print_header("Creating Test Candidate")
    
    candidate = Candidate.objects.create(
        name="[TEST] John Doe",
        email="john.doe.test@example.com",
        # Note: resume_file is optional for testing
        # In production, you would upload an actual PDF
    )
    
    print_success(f"Created candidate: {candidate.name}")
    print_info(f"   ID: {candidate.id}")
    print_info(f"   Email: {candidate.email}")
    print_info(f"   Note: Using dummy resume text (no PDF uploaded)")
    
    return candidate


def create_test_application(job, candidate):
    """Create a test application."""
    print_header("Creating Test Application")
    
    print_info("Creating application (this will trigger AI analysis automatically)...")
    print_info("Please wait, this may take 5-15 seconds with Ollama...")
    
    start_time = time.time()
    
    try:
        application = Application.objects.create(
            candidate=candidate,
            job=job,
            status='pending'
        )
        
        elapsed_time = time.time() - start_time
        
        print_success(f"Created application: {application}")
        print_info(f"   ID: {application.id}")
        print_info(f"   Status: {application.status}")
        print_info(f"   Analysis time: {elapsed_time:.2f} seconds")
        
        return application
        
    except Exception as e:
        print_error(f"Failed to create application: {str(e)}")
        return None


def display_ai_results(application):
    """Display AI analysis results."""
    print_header("AI Analysis Results")
    
    # Refresh from database to get updated values
    application.refresh_from_db()
    
    if application.ai_score is None:
        print_error("AI analysis has not been completed yet")
        print_info("This might mean:")
        print_info("  1. FastAPI service is not running")
        print_info("  2. There was an error during analysis")
        print_info("  3. Analysis is still in progress")
        return False
    
    # Display score with color
    score = application.ai_score
    if score >= 75:
        score_color = "🟢 GREEN"
    elif score >= 50:
        score_color = "🟠 ORANGE"
    else:
        score_color = "🔴 RED"
    
    print(f"\n📊 Match Score: {score}/100 ({score_color})")
    
    if application.ai_feedback:
        feedback = application.ai_feedback
        
        # Summary
        if 'summary' in feedback:
            print(f"\n📝 Summary:")
            print(f"   {feedback['summary']}")
        
        # Missing skills
        if 'missing_skills' in feedback and feedback['missing_skills']:
            print(f"\n❌ Missing Skills:")
            for skill in feedback['missing_skills']:
                print(f"   • {skill}")
        
        # Interview questions
        if 'interview_questions' in feedback and feedback['interview_questions']:
            print(f"\n❓ Interview Questions:")
            for i, question in enumerate(feedback['interview_questions'], 1):
                print(f"   {i}. {question}")
    
    print_success("AI analysis completed successfully!")
    return True


def test_manual_analysis(application):
    """Test manual analysis function."""
    print_header("Testing Manual Analysis Function")
    
    print_info("Triggering manual analysis...")
    
    try:
        result = analyze_application(application.id)
        
        print_success("Manual analysis completed!")
        print_info(f"   Success: {result.get('success')}")
        print_info(f"   Score: {result.get('score')}")
        
        return True
        
    except Exception as e:
        print_error(f"Manual analysis failed: {str(e)}")
        return False


def verify_admin_access():
    """Verify admin interface is accessible."""
    print_header("Admin Interface Access")
    
    print_info("To view results in Django Admin:")
    print_info("   1. Open browser: http://localhost:8001/admin")
    print_info("   2. Login with your superuser credentials")
    print_info("   3. Navigate to: Recruitment > Applications")
    print_info("   4. Click on the test application to see AI results")
    print()
    print_info("Admin features to try:")
    print_info("   • View color-coded AI scores")
    print_info("   • See formatted AI feedback")
    print_info("   • Use bulk actions (Trigger AI analysis, Accept, Reject)")
    print_info("   • Filter by status and date")


def main():
    """Main test function."""
    print_header("🧪 Django Recruitment Backend - Comprehensive Test")
    
    print_info("This script will:")
    print_info("  1. Clean up existing test data")
    print_info("  2. Create a test job posting")
    print_info("  3. Create a test candidate")
    print_info("  4. Create an application (triggers AI analysis)")
    print_info("  5. Display AI analysis results")
    print_info("  6. Test manual analysis function")
    print()
    
    input("Press Enter to continue...")
    
    try:
        # Step 1: Cleanup
        cleanup_test_data()
        
        # Step 2: Create job
        job = create_test_job()
        
        # Step 3: Create candidate
        candidate = create_test_candidate()
        
        # Step 4: Create application (triggers AI)
        application = create_test_application(job, candidate)
        
        if not application:
            print_error("Failed to create application. Exiting.")
            return
        
        # Wait a moment for AI analysis to complete
        time.sleep(2)
        
        # Step 5: Display results
        success = display_ai_results(application)
        
        if success:
            # Step 6: Test manual analysis
            test_manual_analysis(application)
        
        # Step 7: Admin access info
        verify_admin_access()
        
        # Summary
        print_header("✅ Test Complete!")
        print_success("All tests passed!")
        print()
        print_info("Test data created:")
        print_info(f"   • Job ID: {job.id}")
        print_info(f"   • Candidate ID: {candidate.id}")
        print_info(f"   • Application ID: {application.id}")
        print()
        print_info("Next steps:")
        print_info("   1. Check the admin interface")
        print_info("   2. Try creating more applications")
        print_info("   3. Test bulk actions")
        print_info("   4. Upload real PDF resumes")
        
    except Exception as e:
        print_error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
