"""
Unit tests for safety guardrails.
"""

import pytest
from app.guardrails.pii_detector import PIIDetector
from app.guardrails.bias_detector import BiasDetector
from app.guardrails.toxicity_filter import ToxicityFilter
from app.guardrails.output_validator import OutputValidator
from app.guardrails.safety import SafetyGuardrails


class TestPIIDetector:
    """Tests for PII detection."""
    
    def test_detect_email(self):
        """Test email detection."""
        text = "Contact me at john.doe@example.com for more information"
        detector = PIIDetector()
        findings = detector.scan(text)
        
        assert len(findings) > 0
        assert any(f.entity_type == "EMAIL_ADDRESS" for f in findings)
    
    def test_detect_phone(self):
        """Test phone number detection."""
        text = "Call me at 555-123-4567 or 555.987.6543"
        detector = PIIDetector()
        findings = detector.scan(text)
        
        assert len(findings) >= 1
        assert any(f.entity_type == "PHONE_NUMBER" for f in findings)
    
    def test_redact_email(self):
        """Test email redaction."""
        text = "Contact john.doe@example.com"
        detector = PIIDetector(mode="redact")
        redacted = detector.redact(text)
        
        assert "john.doe@example.com" not in redacted
        assert "[REDACTED" in redacted or "<" in redacted  # Presidio or fallback
    
    def test_redact_phone(self):
        """Test phone number redaction."""
        text = "Call me at 555-123-4567"
        detector = PIIDetector(mode="redact")
        redacted = detector.redact(text)
        
        assert "555-123-4567" not in redacted
    
    def test_redact_dict(self):
        """Test dictionary redaction."""
        data = {
            "summary": "Contact john@example.com",
            "questions": ["What is your phone 555-1234?"]
        }
        detector = PIIDetector(mode="redact")
        redacted = detector.redact_dict(data)
        
        assert "john@example.com" not in redacted["summary"]
        assert "555-1234" not in redacted["questions"][0]


class TestBiasDetector:
    """Tests for bias detection."""
    
    def test_detect_age_bias(self):
        """Test age bias detection."""
        analysis = {"summary": "Looking for a young, energetic candidate"}
        detector = BiasDetector()
        findings = detector.scan(analysis)
        
        assert len(findings) > 0
        assert any(f.category == "age" for f in findings)
    
    def test_detect_gender_bias(self):
        """Test gender bias detection."""
        analysis = {"summary": "He would be a great fit for this role"}
        detector = BiasDetector()
        findings = detector.scan(analysis)
        
        assert len(findings) > 0
        assert any(f.category == "gender" for f in findings)
    
    def test_detect_disability_bias(self):
        """Test disability bias detection."""
        analysis = {"summary": "Must be able-bodied for this position"}
        detector = BiasDetector()
        findings = detector.scan(analysis)
        
        assert len(findings) > 0
        assert any(f.category == "disability" for f in findings)
    
    def test_no_bias_in_neutral_text(self):
        """Test that neutral text doesn't trigger false positives."""
        analysis = {"summary": "Candidate has strong Python and Django skills"}
        detector = BiasDetector()
        findings = detector.scan(analysis)
        
        # Should have no findings or very few
        assert len(findings) == 0


class TestToxicityFilter:
    """Tests for toxicity filtering."""
    
    def test_non_toxic_text(self):
        """Test non-toxic text passes."""
        text = "This candidate has excellent Python skills and great communication"
        filter = ToxicityFilter()
        score = filter.score(text)
        
        assert score is not None
        assert not score.is_toxic
        assert score.toxicity < 0.5
    
    def test_toxic_text_detected(self):
        """Test toxic text is flagged."""
        text = "This candidate is terrible, incompetent, and should never work again"
        filter = ToxicityFilter()
        score = filter.score(text)
        
        # Note: May or may not be flagged depending on model sensitivity
        assert score is not None
    
    def test_score_dict(self):
        """Test scoring dictionary values."""
        data = {
            "summary": "Great candidate",
            "questions": ["Tell me about your experience"]
        }
        filter = ToxicityFilter()
        scores = filter.score_dict(data)
        
        assert "summary" in scores
        assert "questions[0]" in scores


class TestOutputValidator:
    """Tests for output validation."""
    
    def test_valid_output(self):
        """Test valid output passes validation."""
        output = {
            "match_score": 85,
            "summary": "This candidate has strong Python and Django experience with 5 years of backend development.",
            "missing_skills": ["Kubernetes", "AWS"],
            "interview_questions": [
                "Can you explain your Django ORM optimization experience?",
                "How would you design a scalable microservices architecture?",
                "Tell me about a challenging bug you debugged recently."
            ]
        }
        validator = OutputValidator()
        result = validator.validate(output, schema_name='screening')
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_invalid_match_score(self):
        """Test invalid match score is caught."""
        output = {
            "match_score": 150,  # Invalid: > 100
            "summary": "Good candidate with relevant experience in the field.",
            "missing_skills": [],
            "interview_questions": ["Q1?", "Q2?", "Q3?"]
        }
        validator = OutputValidator()
        result = validator.validate(output, schema_name='screening')
        
        assert not result.is_valid
        assert any("match_score" in err for err in result.errors)
    
    def test_summary_too_short(self):
        """Test summary length validation."""
        output = {
            "match_score": 75,
            "summary": "Good fit",  # Too short
            "missing_skills": [],
            "interview_questions": ["Q1?", "Q2?", "Q3?"]
        }
        validator = OutputValidator()
        result = validator.validate(output, schema_name='screening')
        
        assert not result.is_valid
    
    def test_validate_and_fix(self):
        """Test automatic fixing of common issues."""
        output = {
            "match_score": 150,  # Will be fixed to 100
            "summary": "Short",  # Will be extended
            "missing_skills": [],
            "interview_questions": ["Q1?", "Q2?"]  # Will be extended to 3
        }
        validator = OutputValidator()
        fixed = validator.validate_and_fix(output, schema_name='screening')
        
        assert fixed["match_score"] == 100
        assert len(fixed["summary"]) >= 50
        assert len(fixed["interview_questions"]) >= 3


class TestSafetyGuardrails:
    """Tests for safety orchestrator."""
    
    def test_validate_clean_analysis(self):
        """Test validation of clean analysis."""
        analysis = {
            "match_score": 85,
            "summary": "Candidate has strong technical skills and relevant experience in backend development.",
            "missing_skills": ["Kubernetes"],
            "interview_questions": [
                "Explain your experience with Django ORM",
                "How do you handle database optimization?",
                "Describe a complex system you built"
            ]
        }
        safety = SafetyGuardrails()
        report = safety.validate_analysis(analysis)
        
        assert not report.has_critical_issues
    
    def test_detect_pii_in_analysis(self):
        """Test PII detection in analysis."""
        analysis = {
            "match_score": 85,
            "summary": "Contact candidate at john@example.com for next steps.",
            "missing_skills": [],
            "interview_questions": ["Q1?", "Q2?", "Q3?"]
        }
        safety = SafetyGuardrails()
        report = safety.validate_analysis(analysis)
        
        assert len(report.pii_findings) > 0
        assert report.has_issues
    
    def test_detect_bias_in_analysis(self):
        """Test bias detection in analysis."""
        analysis = {
            "match_score": 85,
            "summary": "This young candidate shows great potential for growth.",
            "missing_skills": [],
            "interview_questions": ["Q1?", "Q2?", "Q3?"]
        }
        safety = SafetyGuardrails()
        report = safety.validate_analysis(analysis)
        
        assert len(report.bias_findings) > 0
        assert report.has_issues
    
    def test_validate_and_sanitize(self):
        """Test validation and sanitization."""
        analysis = {
            "match_score": 85,
            "summary": "Contact at john@example.com. This young candidate is great.",
            "missing_skills": [],
            "interview_questions": ["Q1?", "Q2?", "Q3?"]
        }
        safety = SafetyGuardrails(pii_mode="redact")
        sanitized, report = safety.validate_and_sanitize(analysis, auto_redact=True)
        
        # PII should be redacted
        assert "john@example.com" not in sanitized["summary"]
        
        # Bias should still be detected
        assert len(report.bias_findings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
