"""
Test script for safety guardrails.

Run this to verify guardrails are working correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from app.guardrails.safety import SafetyGuardrails


async def main():
    print("=" * 60)
    print("Testing Safety Guardrails")
    print("=" * 60)
    
    # Initialize guardrails
    safety = SafetyGuardrails(pii_mode="flag")
    
    # Test case 1: Clean analysis
    print("\n1. Testing clean analysis...")
    clean_analysis = {
        "match_score": 85,
        "summary": "Candidate has strong Python and Django experience with excellent problem-solving skills.",
        "missing_skills": ["Kubernetes", "AWS"],
        "interview_questions": [
            "Can you explain your Django ORM optimization experience?",
            "How would you design a scalable microservices architecture?",
            "Tell me about a challenging bug you debugged recently."
        ]
    }
    
    report = safety.validate_analysis(clean_analysis)
    print(f"   Result: {report.summary()}")
    print(f"   Has issues: {report.has_issues}")
    
    # Test case 2: Analysis with PII
    print("\n2. Testing PII detection...")
    pii_analysis = {
        "match_score": 90,
        "summary": "Excellent candidate. Contact at john.doe@example.com or call 555-123-4567.",
        "missing_skills": [],
        "interview_questions": [
            "Tell me about your experience",
            "What are your salary expectations?",
            "When can you start?"
        ]
    }
    
    report = safety.validate_analysis(pii_analysis)
    print(f"   Result: {report.summary()}")
    print(f"   PII findings: {len(report.pii_findings)}")
    for finding in report.pii_findings:
        print(f"      - {finding.entity_type} at position {finding.start}-{finding.end}")
    
    # Test case 3: Analysis with bias
    print("\n3. Testing bias detection...")
    biased_analysis = {
        "match_score": 75,
        "summary": "This young, energetic candidate would be a great cultural fit for our team.",
        "missing_skills": ["Experience"],
        "interview_questions": [
            "Are you comfortable working long hours?",
            "Do you have family commitments?",
            "What does your husband/wife think about this role?"
        ]
    }
    
    report = safety.validate_analysis(biased_analysis)
    print(f"   Result: {report.summary()}")
    print(f"   Bias findings: {len(report.bias_findings)}")
    for finding in report.bias_findings:
        print(f"      - {finding.category}: '{finding.keyword}' ({finding.severity})")
    
    # Test case 4: Invalid output structure
    print("\n4. Testing output validation...")
    invalid_analysis = {
        "match_score": 150,  # Invalid: > 100
        "summary": "Too short",  # Invalid: < 50 chars
        "missing_skills": [],
        "interview_questions": ["Q1?"]  # Invalid: < 3 questions
    }
    
    report = safety.validate_analysis(invalid_analysis)
    print(f"   Result: {report.summary()}")
    if report.validation_result:
        print(f"   Validation errors: {len(report.validation_result.errors)}")
        for error in report.validation_result.errors[:3]:
            print(f"      - {error}")
    
    # Test case 5: Sanitization
    print("\n5. Testing sanitization...")
    dirty_analysis = {
        "match_score": 85,
        "summary": "Great candidate! Contact at jane@example.com. She has excellent skills.",
        "missing_skills": [],
        "interview_questions": [
            "Tell me about yourself",
            "What are your strengths?",
            "Where do you see yourself in 5 years?"
        ]
    }
    
    sanitized, report = safety.validate_and_sanitize(dirty_analysis, auto_redact=True)
    print(f"   Original summary: {dirty_analysis['summary'][:50]}...")
    print(f"   Sanitized summary: {sanitized['summary'][:50]}...")
    print(f"   Safety report: {report.summary()}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
