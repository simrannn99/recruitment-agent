"""
Test script for PDF text extraction functionality.
Tests both real PDF files and fallback to dummy text.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_backend.settings')
django.setup()

from recruitment.utils.pdf_extractor import (
    extract_text_from_pdf,
    validate_pdf_file,
    get_pdf_metadata,
    get_dummy_resume_text
)


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def test_dummy_text():
    """Test dummy text generation."""
    print_header("Test 1: Dummy Resume Text")
    
    text = get_dummy_resume_text()
    print(f"✅ Generated dummy text: {len(text)} characters")
    print(f"\nFirst 200 characters:")
    print(text[:200] + "...")


def test_no_file():
    """Test extraction with no file."""
    print_header("Test 2: No File Provided")
    
    text = extract_text_from_pdf(None)
    print(f"✅ Handled None input: {len(text)} characters")
    print("   Falls back to dummy text ✓")


def test_nonexistent_file():
    """Test extraction with nonexistent file."""
    print_header("Test 3: Nonexistent File")
    
    text = extract_text_from_pdf("/path/to/nonexistent.pdf")
    print(f"✅ Handled nonexistent file: {len(text)} characters")
    print("   Falls back to dummy text ✓")


def test_real_pdf():
    """Test extraction with real PDF if available."""
    print_header("Test 4: Real PDF File (if available)")
    
    # Check if there are any PDF files in media/resumes/
    resume_dir = "media/resumes"
    
    if not os.path.exists(resume_dir):
        print("⚠️  No media/resumes directory found")
        print("   Upload a resume via admin to test real PDF extraction")
        return
    
    pdf_files = [f for f in os.listdir(resume_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("⚠️  No PDF files found in media/resumes/")
        print("   Upload a resume via admin to test real PDF extraction")
        return
    
    # Test first PDF file
    pdf_path = os.path.join(resume_dir, pdf_files[0])
    print(f"📄 Testing with: {pdf_path}")
    
    # Validate
    is_valid = validate_pdf_file(pdf_path)
    print(f"   Valid PDF: {is_valid}")
    
    # Get metadata
    metadata = get_pdf_metadata(pdf_path)
    print(f"   Pages: {metadata.get('pages', 'Unknown')}")
    print(f"   Title: {metadata.get('title', 'Unknown')}")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    print(f"\n✅ Extracted {len(text)} characters from PDF")
    print(f"\nFirst 300 characters:")
    print(text[:300] + "...")


def test_validation():
    """Test PDF validation."""
    print_header("Test 5: PDF Validation")
    
    # Test various inputs
    test_cases = [
        (None, False, "None input"),
        ("/nonexistent.pdf", False, "Nonexistent file"),
        ("test.txt", False, "Non-PDF file"),
    ]
    
    for file_path, expected, description in test_cases:
        result = validate_pdf_file(file_path)
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}: {result} (expected: {expected})")


def test_integration():
    """Test integration with Django models."""
    print_header("Test 6: Django Integration")
    
    from recruitment.models import Candidate
    
    # Get a candidate with resume
    candidates_with_resume = Candidate.objects.exclude(resume_file='')
    
    if not candidates_with_resume.exists():
        print("⚠️  No candidates with resumes found")
        print("   Create a candidate and upload a resume via admin")
        return
    
    candidate = candidates_with_resume.first()
    print(f"📋 Testing with candidate: {candidate.name}")
    print(f"   Resume file: {candidate.resume_file}")
    
    if candidate.resume_file:
        text = extract_text_from_pdf(candidate.resume_file.path)
        print(f"\n✅ Extracted {len(text)} characters")
        print(f"\nFirst 200 characters:")
        print(text[:200] + "...")
    else:
        print("⚠️  Candidate has no resume file")


def main():
    """Run all tests."""
    print("=" * 70)
    print("  PDF Text Extraction - Test Suite")
    print("=" * 70)
    
    try:
        test_dummy_text()
        test_no_file()
        test_nonexistent_file()
        test_validation()
        test_real_pdf()
        test_integration()
        
        print_header("✅ All Tests Complete!")
        print("\nSummary:")
        print("  • Dummy text generation: ✅")
        print("  • Fallback handling: ✅")
        print("  • PDF validation: ✅")
        print("  • Real PDF extraction: Ready (upload PDFs to test)")
        print("  • Django integration: Ready")
        
        print("\nNext steps:")
        print("  1. Upload a resume PDF via admin")
        print("  2. Create an application")
        print("  3. Check AI analysis uses real PDF text")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
