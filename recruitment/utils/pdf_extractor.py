"""
Utility functions for PDF text extraction.
"""
import os
from pathlib import Path


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file (can be string or File object)
        
    Returns:
        str: Extracted text from the PDF
        
    Note:
        This is a placeholder function. In production, you would use a library
        like PyPDF2, pdfplumber, or pypdf to extract actual text.
        
    Example implementation with PyPDF2:
        ```python
        import PyPDF2
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        ```
    """
    # Handle case where pdf_path is empty or None (no file uploaded)
    if not pdf_path:
        return get_dummy_resume_text()
    
    # Convert to string if it's a file field
    pdf_path_str = str(pdf_path)
    
    # Check if file exists
    if not os.path.exists(pdf_path_str):
        # Return dummy text for testing
        return get_dummy_resume_text()
    
    # Placeholder implementation returning dummy text
    # TODO: Replace with actual PDF extraction logic
    return get_dummy_resume_text()


def get_dummy_resume_text():
    """
    Get dummy resume text for testing.
    
    Returns:
        str: Dummy resume text
    """
    dummy_resume_text = """
    John Doe
    Senior Software Engineer
    
    EXPERIENCE:
    - 5 years of Python development
    - Expert in Django and FastAPI frameworks
    - Experience with PostgreSQL and MongoDB databases
    - Proficient in Docker and Kubernetes
    - AWS cloud services (EC2, S3, Lambda, RDS)
    - CI/CD pipelines with GitHub Actions
    - RESTful API design and development
    - Agile/Scrum methodologies
    
    SKILLS:
    - Languages: Python, JavaScript, SQL
    - Frameworks: Django, FastAPI, Flask, React
    - Databases: PostgreSQL, MongoDB, Redis
    - DevOps: Docker, Kubernetes, AWS, CI/CD
    - Tools: Git, GitHub, VS Code, Postman
    
    EDUCATION:
    - B.S. Computer Science, University of Technology
    
    PROJECTS:
    - Built scalable microservices architecture handling 1M+ requests/day
    - Developed RESTful APIs for e-commerce platform
    - Implemented automated testing and deployment pipelines
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
    
    if not os.path.exists(file_path):
        return False
    
    # Check file extension
    if not str(file_path).lower().endswith('.pdf'):
        return False
    
    return True
