"""
Quick test script to verify Ollama integration with the recruitment agent.
"""

import requests
import json

def test_ollama_integration():
    """Test the recruitment agent with Ollama."""
    
    # API endpoint
    url = "http://localhost:8000/analyze"
    
    # Sample job description and resume
    test_data = {
        "job_description": """
        We are looking for a Python Backend Developer with experience in:
        - FastAPI or Django
        - RESTful API design
        - PostgreSQL or MongoDB
        - Docker and containerization
        - AWS or GCP cloud platforms
        - CI/CD pipelines
        """,
        "resume_text": """
        John Doe
        Backend Developer
        
        Experience:
        - 3 years of Python development
        - Built RESTful APIs using FastAPI
        - Worked with PostgreSQL databases
        - Experience with Docker containerization
        - Familiar with AWS services (EC2, S3, Lambda)
        
        Skills:
        - Python, FastAPI, Flask
        - PostgreSQL, Redis
        - Docker, Git
        - AWS (EC2, S3, Lambda)
        """
    }
    
    print("🚀 Testing Ollama integration with recruitment agent...")
    print(f"📍 Endpoint: {url}")
    print("\n" + "="*60)
    
    try:
        # Make the request
        print("⏳ Analyzing resume (this may take a moment with local LLM)...")
        response = requests.post(url, json=test_data, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ SUCCESS! Ollama is working correctly!\n")
            print("="*60)
            print(f"📊 Match Score: {result.get('match_score', 'N/A')}/100")
            print(f"\n📝 Summary:\n{result.get('summary', 'N/A')}")
            print(f"\n❌ Missing Skills:\n" + "\n".join(f"  - {skill}" for skill in result.get('missing_skills', [])))
            print(f"\n❓ Interview Questions:")
            for i, question in enumerate(result.get('interview_questions', []), 1):
                print(f"  {i}. {question}")
            print("="*60)
            
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("\n⏱️  Request timed out. The local LLM might be taking longer than expected.")
        print("This is normal for the first request. Try again!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Make sure the server is running!")
        print("Run: python -m uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    test_ollama_integration()
