"""
Django management command to populate test data for recruitment platform.
Usage: python manage.py populate_test_data
"""

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from recruitment.models import JobPosting, Candidate, Application
import random
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Populate database with test data for recruitment platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Application.objects.all().delete()
            Candidate.objects.all().delete()
            JobPosting.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Data cleared'))

        self.stdout.write(self.style.SUCCESS('Populating test data...'))

        # Create job postings
        jobs = self.create_job_postings()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(jobs)} job postings'))

        # Create candidates
        candidates = self.create_candidates()
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(candidates)} candidates'))

        # Create applications
        applications = self.create_applications(jobs, candidates)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(applications)} applications'))

        self.stdout.write(self.style.SUCCESS('\n🎉 Test data populated successfully!'))
        self.stdout.write(self.style.SUCCESS(f'   Jobs: {len(jobs)}'))
        self.stdout.write(self.style.SUCCESS(f'   Candidates: {len(candidates)}'))
        self.stdout.write(self.style.SUCCESS(f'   Applications: {len(applications)}'))
        
        # Show embedding generation status
        self.stdout.write(self.style.SUCCESS('\n📊 Vector Search Status:'))
        self.stdout.write(self.style.WARNING('   Embedding generation tasks queued in Celery'))
        self.stdout.write(self.style.WARNING('   Monitor progress at: http://localhost:5555'))
        self.stdout.write(self.style.SUCCESS('\n💡 Next Steps:'))
        self.stdout.write('   1. Wait 10-20 seconds for embeddings to generate')
        self.stdout.write('   2. Check status: python manage.py generate_embeddings --stats')
        self.stdout.write('   3. Test search: python scripts\\test_vector_search.py')
        self.stdout.write('   4. Try API: POST http://localhost:8001/api/search/candidates/')

    def create_job_postings(self):
        """Create sample job postings."""
        jobs_data = [
            {
                'title': 'Senior Python Developer',
                'description': '''We are seeking a Senior Python Developer to join our backend team.

Requirements:
- 5+ years of Python development experience
- Strong experience with Django and FastAPI
- Knowledge of PostgreSQL and database optimization
- Experience with Docker and containerization
- Familiarity with Celery and async task processing
- Understanding of microservices architecture
- Experience with REST API design
- Knowledge of Git and CI/CD pipelines

Nice to have:
- Experience with RabbitMQ or Redis
- Knowledge of LangChain or LLM integration
- AWS or cloud deployment experience
- Experience with monitoring tools (Flower, Prometheus)

Responsibilities:
- Design and implement scalable backend services
- Optimize database queries and API performance
- Mentor junior developers
- Participate in code reviews and architecture decisions
- Collaborate with frontend and DevOps teams'''
            },
            {
                'title': 'Full Stack Engineer',
                'description': '''Looking for a Full Stack Engineer to build modern web applications.

Requirements:
- 3+ years of full stack development
- Proficiency in React and TypeScript
- Backend experience with Node.js or Python
- Experience with PostgreSQL or MongoDB
- Understanding of RESTful API design
- Knowledge of Docker and deployment
- Familiarity with Git workflows

Nice to have:
- Experience with Next.js or FastAPI
- Knowledge of GraphQL
- AWS or Azure experience
- Understanding of CI/CD pipelines

Responsibilities:
- Build responsive web applications
- Develop and maintain APIs
- Collaborate with design team
- Write clean, maintainable code
- Participate in agile development process'''
            },
            {
                'title': 'DevOps Engineer',
                'description': '''Seeking a DevOps Engineer to manage our infrastructure and deployment pipelines.

Requirements:
- 4+ years of DevOps experience
- Strong knowledge of Docker and Kubernetes
- Experience with AWS, GCP, or Azure
- Proficiency in CI/CD tools (Jenkins, GitLab CI, GitHub Actions)
- Knowledge of infrastructure as code (Terraform, CloudFormation)
- Experience with monitoring and logging (Prometheus, Grafana, ELK)
- Strong scripting skills (Python, Bash)
- Understanding of networking and security

Nice to have:
- Experience with service mesh (Istio, Linkerd)
- Knowledge of GitOps practices
- Experience with database administration
- Familiarity with message queues (RabbitMQ, Kafka)

Responsibilities:
- Manage cloud infrastructure
- Implement and maintain CI/CD pipelines
- Monitor system performance and reliability
- Automate deployment processes
- Ensure security and compliance'''
            },
            {
                'title': 'Machine Learning Engineer',
                'description': '''We need a Machine Learning Engineer to develop AI-powered features.

Requirements:
- 3+ years of ML/AI experience
- Strong Python programming skills
- Experience with PyTorch or TensorFlow
- Knowledge of NLP and LLMs
- Understanding of model deployment and MLOps
- Experience with data preprocessing and feature engineering
- Familiarity with cloud ML services (AWS SageMaker, GCP AI Platform)

Nice to have:
- Experience with LangChain or similar frameworks
- Knowledge of vector databases (Pinecone, Weaviate)
- Experience with fine-tuning LLMs
- Understanding of RAG (Retrieval-Augmented Generation)
- Experience with model monitoring and versioning

Responsibilities:
- Develop and deploy ML models
- Integrate LLMs into applications
- Optimize model performance
- Collaborate with backend team
- Research new AI techniques'''
            },
            {
                'title': 'Frontend Developer',
                'description': '''Looking for a Frontend Developer to create beautiful user interfaces.

Requirements:
- 2+ years of frontend development
- Expert knowledge of React and modern JavaScript
- Experience with TypeScript
- Strong CSS skills (Tailwind, styled-components)
- Understanding of responsive design
- Knowledge of state management (Redux, Zustand)
- Experience with testing (Jest, React Testing Library)

Nice to have:
- Experience with Next.js
- Knowledge of accessibility standards
- Experience with design systems
- Familiarity with Figma or similar tools

Responsibilities:
- Build responsive web applications
- Implement pixel-perfect designs
- Optimize frontend performance
- Write reusable components
- Collaborate with designers and backend team'''
            }
        ]

        jobs = []
        for job_data in jobs_data:
            job = JobPosting.objects.create(**job_data)
            jobs.append(job)

        return jobs

    def create_candidates(self):
        """Create sample candidates with realistic profiles."""
        candidates_data = [
            {
                'name': 'Alice Johnson',
                'email': 'alice.johnson@email.com',
                'resume_text': '''ALICE JOHNSON
Senior Python Developer

EXPERIENCE:
- 6 years of Python development
- Expert in Django and FastAPI
- Strong PostgreSQL and database optimization skills
- Extensive Docker and Kubernetes experience
- Built microservices with Celery and RabbitMQ
- Implemented CI/CD pipelines with GitHub Actions

SKILLS:
Python, Django, FastAPI, PostgreSQL, Docker, Kubernetes, Celery, RabbitMQ, Redis, Git, AWS

EDUCATION:
BS Computer Science, MIT'''
            },
            {
                'name': 'Bob Smith',
                'email': 'bob.smith@email.com',
                'resume_text': '''BOB SMITH
Full Stack Developer

EXPERIENCE:
- 4 years of full stack development
- Proficient in React, TypeScript, and Node.js
- Experience with PostgreSQL and MongoDB
- Built RESTful APIs and GraphQL services
- Deployed applications on AWS

SKILLS:
React, TypeScript, Node.js, Express, PostgreSQL, MongoDB, Docker, AWS, Git

EDUCATION:
BS Software Engineering, Stanford University'''
            },
            {
                'name': 'Carol Williams',
                'email': 'carol.williams@email.com',
                'resume_text': '''CAROL WILLIAMS
DevOps Engineer

EXPERIENCE:
- 5 years of DevOps experience
- Expert in Docker, Kubernetes, and Terraform
- Managed AWS infrastructure for large-scale applications
- Implemented CI/CD with Jenkins and GitLab
- Set up monitoring with Prometheus and Grafana

SKILLS:
Docker, Kubernetes, Terraform, AWS, Jenkins, GitLab CI, Prometheus, Grafana, Python, Bash

EDUCATION:
MS Computer Science, UC Berkeley'''
            },
            {
                'name': 'David Brown',
                'email': 'david.brown@email.com',
                'resume_text': '''DAVID BROWN
Machine Learning Engineer

EXPERIENCE:
- 4 years of ML/AI experience
- Built NLP models with PyTorch
- Deployed models using AWS SageMaker
- Experience with LangChain and LLM integration
- Implemented RAG systems with vector databases

SKILLS:
Python, PyTorch, TensorFlow, LangChain, NLP, LLMs, AWS SageMaker, Pinecone, FastAPI

EDUCATION:
PhD Machine Learning, Carnegie Mellon University'''
            },
            {
                'name': 'Emma Davis',
                'email': 'emma.davis@email.com',
                'resume_text': '''EMMA DAVIS
Frontend Developer

EXPERIENCE:
- 3 years of frontend development
- Expert in React and TypeScript
- Built responsive applications with Tailwind CSS
- Experience with Next.js and state management
- Strong focus on accessibility and performance

SKILLS:
React, TypeScript, Next.js, Tailwind CSS, Redux, Jest, Figma, Git

EDUCATION:
BS Computer Science, Georgia Tech'''
            },
            {
                'name': 'Frank Miller',
                'email': 'frank.miller@email.com',
                'resume_text': '''FRANK MILLER
Junior Python Developer

EXPERIENCE:
- 1 year of Python development
- Basic Django knowledge
- Familiar with PostgreSQL
- Learning Docker and containerization

SKILLS:
Python, Django, PostgreSQL, Git, HTML, CSS

EDUCATION:
BS Computer Science, University of Washington'''
            },
            {
                'name': 'Grace Lee',
                'email': 'grace.lee@email.com',
                'resume_text': '''GRACE LEE
Senior Full Stack Engineer

EXPERIENCE:
- 7 years of full stack development
- Expert in React, Node.js, and Python
- Built scalable microservices architecture
- Experience with AWS and GCP
- Led team of 5 developers

SKILLS:
React, Node.js, Python, Django, PostgreSQL, MongoDB, Docker, Kubernetes, AWS, GCP

EDUCATION:
MS Software Engineering, Cornell University'''
            },
            {
                'name': 'Henry Wilson',
                'email': 'henry.wilson@email.com',
                'resume_text': '''HENRY WILSON
Cloud Architect

EXPERIENCE:
- 8 years of cloud and DevOps experience
- Designed multi-region AWS architectures
- Expert in Terraform and CloudFormation
- Implemented zero-downtime deployments
- Strong security and compliance knowledge

SKILLS:
AWS, GCP, Terraform, CloudFormation, Kubernetes, Docker, Python, Security, Compliance

EDUCATION:
BS Computer Engineering, Purdue University'''
            }
        ]

        candidates = []
        for candidate_data in candidates_data:
            # Create candidate with resume_text_cache for embedding generation
            candidate = Candidate.objects.create(
                name=candidate_data['name'],
                email=candidate_data['email'],
                resume_text_cache=candidate_data['resume_text']  # Save resume text for embeddings
            )
            candidates.append(candidate)

        return candidates

    def create_applications(self, jobs, candidates):
        """Create sample applications."""
        applications = []
        statuses = ['pending', 'under_review', 'accepted', 'rejected']

        # Create strategic applications
        application_mapping = [
            # Alice (Senior Python Dev) - perfect match for Senior Python Developer
            (candidates[0], jobs[0], 'accepted', 92),
            # Bob (Full Stack) - good match for Full Stack Engineer
            (candidates[1], jobs[1], 'accepted', 88),
            # Carol (DevOps) - perfect match for DevOps Engineer
            (candidates[2], jobs[2], 'accepted', 95),
            # David (ML Engineer) - perfect match for ML Engineer
            (candidates[3], jobs[3], 'accepted', 90),
            # Emma (Frontend) - perfect match for Frontend Developer
            (candidates[4], jobs[4], 'accepted', 87),
            # Frank (Junior) - applied to Senior Python Developer (mismatch)
            (candidates[5], jobs[0], 'rejected', 45),
            # Grace (Senior Full Stack) - applied to Full Stack Engineer
            (candidates[6], jobs[1], 'pending', 93),
            # Henry (Cloud Architect) - applied to DevOps Engineer
            (candidates[7], jobs[2], 'pending', 89),
            # Alice also applied to ML Engineer (cross-application)
            (candidates[0], jobs[3], 'pending', None),
            # Bob applied to Frontend Developer
            (candidates[1], jobs[4], 'pending', None),
        ]

        for candidate, job, status, score in application_mapping:
            application = Application.objects.create(
                candidate=candidate,
                job=job,
                status=status
            )
            
            # Set AI score and feedback for processed applications
            if score:
                application.ai_score = score
                application.ai_feedback = {
                    'summary': f'Candidate shows strong alignment with job requirements. Score: {score}/100',
                    'missing_skills': self.get_missing_skills(score),
                    'interview_questions': self.get_interview_questions(job.title)
                }
                application.save()

            applications.append(application)

        return applications

    def get_missing_skills(self, score):
        """Generate missing skills based on score."""
        if score >= 90:
            return []
        elif score >= 80:
            return ['Advanced cloud architecture', 'Team leadership']
        elif score >= 70:
            return ['Production deployment experience', 'System design', 'Mentoring']
        else:
            return ['Core technical skills', 'Relevant experience', 'Domain knowledge']

    def get_interview_questions(self, job_title):
        """Generate interview questions based on job title."""
        questions = {
            'Senior Python Developer': [
                'Explain your experience with Django ORM optimization',
                'How would you design a scalable microservices architecture?',
                'Describe your approach to implementing async task processing'
            ],
            'Full Stack Engineer': [
                'How do you ensure consistency between frontend and backend?',
                'Describe your experience with state management in React',
                'How would you optimize API performance?'
            ],
            'DevOps Engineer': [
                'Explain your approach to zero-downtime deployments',
                'How do you implement infrastructure as code?',
                'Describe your experience with container orchestration'
            ],
            'Machine Learning Engineer': [
                'How do you approach model deployment and monitoring?',
                'Explain your experience with LLM integration',
                'Describe a challenging ML problem you solved'
            ],
            'Frontend Developer': [
                'How do you ensure accessibility in your applications?',
                'Describe your approach to responsive design',
                'How do you optimize frontend performance?'
            ]
        }
        return questions.get(job_title, ['Tell me about your experience', 'What are your strengths?', 'Why this role?'])
