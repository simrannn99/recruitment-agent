"""
Example script to test the resume screening API.
"""
import requests
import json


# Example job description
JOB_DESCRIPTION = """
Senior Backend Engineer - Python/FastAPI

We are seeking an experienced Senior Backend Engineer to join our growing team.

Requirements:
- 5+ years of Python development experience
- Strong experience with FastAPI or similar async frameworks
- Experience with PostgreSQL and database design
- Knowledge of Docker and Kubernetes
- Experience with AWS (Lambda, S3, RDS)
- Understanding of microservices architecture
- Experience with CI/CD pipelines
- Strong problem-solving skills

Nice to have:
- Experience with LangChain or LLM integration
- Knowledge of GraphQL
- Experience with event-driven architectures
"""

# Example resume
RESUME_TEXT = """
Jane Smith
Senior Software Engineer

EXPERIENCE

Tech Company Inc. | Senior Software Engineer | 2019 - Present
- Developed REST APIs using Python and Flask
- Designed and implemented PostgreSQL database schemas
- Deployed applications using Docker containers
- Implemented automated testing with pytest
- Collaborated with frontend team on API design

StartupXYZ | Software Engineer | 2017 - 2019
- Built web applications using Python and Django
- Worked with MySQL databases
- Implemented user authentication and authorization
- Participated in code reviews and agile ceremonies

SKILLS
- Languages: Python, JavaScript, SQL
- Frameworks: Flask, Django, React
- Databases: PostgreSQL, MySQL
- Tools: Docker, Git, Jenkins
- Cloud: Basic AWS experience (EC2, S3)

EDUCATION
B.S. Computer Science, University of Technology, 2017
"""


def test_analyze_endpoint():
    """Test the /analyze endpoint."""
    url = "http://localhost:8001/analyze"

    payload = {"job_description": JOB_DESCRIPTION, "resume_text": RESUME_TEXT}

    print("Sending request to API...")
    print("-" * 80)

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()

        print("\n✅ API Response:")
        print("=" * 80)
        print(f"\n📊 Match Score: {result['match_score']}/100")
        print(f"\n📝 Summary:\n{result['summary']}")
        print(f"\n❌ Missing Skills:")
        for skill in result["missing_skills"]:
            print(f"  - {skill}")
        print(f"\n💬 Interview Questions:")
        for i, question in enumerate(result["interview_questions"], 1):
            print(f"  {i}. {question}")
        print("\n" + "=" * 80)

        # Pretty print the full JSON response
        print("\n📄 Full JSON Response:")
        print(json.dumps(result, indent=2))

    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the API.")
        print("Make sure the server is running: uvicorn app.main:app --reload")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_analyze_endpoint()
