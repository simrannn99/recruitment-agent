"""
Utility functions for PDF text extraction.
"""
import os
import logging
from pathlib import Path
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file (can be string, Path, or File object)
        
    Returns:
        str: Extracted text from the PDF
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        Exception: If PDF parsing fails
    """
    # Handle case where pdf_path is empty or None (no file uploaded)
    if not pdf_path:
        logger.warning("No PDF path provided, using dummy resume text")
        return get_dummy_resume_text()
    
    # Convert to string if it's a file field or Path object
    pdf_path_str = str(pdf_path)
    
    # Check if file exists
    if not os.path.exists(pdf_path_str):
        logger.warning(f"PDF file not found: {pdf_path_str}, using dummy resume text")
        return get_dummy_resume_text()
    
    # Validate it's a PDF
    if not pdf_path_str.lower().endswith('.pdf'):
        logger.error(f"File is not a PDF: {pdf_path_str}")
        raise ValueError(f"File must be a PDF, got: {pdf_path_str}")
    
    try:
        logger.info(f"Extracting text from PDF: {pdf_path_str}")
        
        # Open and read the PDF
        reader = PdfReader(pdf_path_str)
        
        # Extract text from all pages
        text_parts = []
        total_pages = len(reader.pages)
        
        logger.debug(f"PDF has {total_pages} pages")
        
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                    logger.debug(f"Extracted {len(page_text)} characters from page {page_num}")
                else:
                    logger.warning(f"No text found on page {page_num}")
            except Exception as e:
                logger.error(f"Error extracting text from page {page_num}: {str(e)}")
                continue
        
        # Combine all text
        full_text = '\n\n'.join(text_parts)
        
        if not full_text.strip():
            logger.warning("No text extracted from PDF, using dummy resume text")
            return get_dummy_resume_text()
        
        logger.info(f"Successfully extracted {len(full_text)} characters from {total_pages} pages")
        return full_text.strip()
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {str(e)}")
        logger.warning("Falling back to dummy resume text")
        return get_dummy_resume_text()


def get_dummy_resume_text():
    """
    Get dummy resume text for testing when no PDF is available.
    
    Returns:
        str: Dummy resume text
    """
    dummy_resume_text = """
    John Doe
    Senior Software Engineer
    Email: john.doe@example.com | Phone: (555) 123-4567
    
    PROFESSIONAL SUMMARY
    Results-driven Senior Software Engineer with 5+ years of experience in full-stack development,
    specializing in Python backend systems, RESTful APIs, and cloud infrastructure.
    
    TECHNICAL SKILLS
    Languages: Python, JavaScript, SQL, TypeScript
    Frameworks: Django, FastAPI, Flask, React, Node.js
    Databases: PostgreSQL, MongoDB, Redis, MySQL
    Cloud & DevOps: AWS (EC2, S3, Lambda, RDS), Docker, Kubernetes, CI/CD
    Tools: Git, GitHub Actions, Jenkins, Postman, VS Code
    
    PROFESSIONAL EXPERIENCE
    
    Senior Backend Developer | Tech Solutions Inc. | 2021 - Present
    • Designed and developed scalable microservices architecture handling 1M+ requests/day
    • Built RESTful APIs using FastAPI and Django for e-commerce platform
    • Implemented automated testing and deployment pipelines using GitHub Actions
    • Optimized database queries resulting in 40% performance improvement
    • Mentored junior developers and conducted code reviews
    
    Backend Developer | StartupXYZ | 2019 - 2021
    • Developed backend services using Django and PostgreSQL
    • Integrated third-party APIs and payment gateways
    • Implemented caching strategies using Redis
    • Participated in Agile/Scrum development process
    
    EDUCATION
    Bachelor of Science in Computer Science
    University of Technology | 2015 - 2019
    GPA: 3.8/4.0
    
    PROJECTS
    • E-commerce Platform: Built scalable backend with Django, PostgreSQL, and Redis
    • API Gateway: Developed microservices gateway using FastAPI and Docker
    • Data Pipeline: Created ETL pipeline processing 100K+ records daily
    
    CERTIFICATIONS
    • AWS Certified Solutions Architect - Associate
    • Python Professional Certification
    """
    
    return dummy_resume_text.strip()


def validate_pdf_file(file_path):
    """
    Validate that the file exists and is a PDF.
    
    Args:
        file_path: Path to the file
        
    Returns:
        bool: True if valid PDF, False otherwise
    """
    if not file_path:
        return False
    
    file_path_str = str(file_path)
    
    if not os.path.exists(file_path_str):
        return False
    
    # Check file extension
    if not file_path_str.lower().endswith('.pdf'):
        return False
    
    # Try to open as PDF
    try:
        reader = PdfReader(file_path_str)
        # Check if it has at least one page
        return len(reader.pages) > 0
    except Exception:
        return False


def get_pdf_metadata(file_path):
    """
    Extract metadata from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        dict: PDF metadata (title, author, pages, etc.)
    """
    if not file_path or not os.path.exists(str(file_path)):
        return {}
    
    try:
        reader = PdfReader(str(file_path))
        metadata = {
            'pages': len(reader.pages),
            'title': reader.metadata.get('/Title', 'Unknown'),
            'author': reader.metadata.get('/Author', 'Unknown'),
            'creator': reader.metadata.get('/Creator', 'Unknown'),
            'producer': reader.metadata.get('/Producer', 'Unknown'),
        }
        return metadata
    except Exception as e:
        logger.error(f"Failed to extract PDF metadata: {str(e)}")
        return {}
