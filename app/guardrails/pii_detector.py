"""
PII detection and redaction using Microsoft Presidio.
"""

from typing import List, Dict, Any
import logging

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logging.warning("Presidio not installed. PII detection will be limited.")

from app.guardrails.models import PIIFinding

logger = logging.getLogger(__name__)


class PIIDetector:
    """
    Detect and redact PII using Microsoft Presidio.
    
    Supports detection of:
    - Email addresses
    - Phone numbers
    - Person names
    - Locations
    - Credit cards
    - IP addresses
    - URLs
    """
    
    PII_ENTITIES = [
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "PERSON",
        "LOCATION",
        "CREDIT_CARD",
        "IBAN_CODE",
        "IP_ADDRESS",
        "DATE_TIME",
        "URL"
    ]
    
    def __init__(self, mode: str = "flag"):
        """
        Initialize PII detector.
        
        Args:
            mode: "flag" to detect only, "redact" to replace PII
        """
        self.mode = mode
        
        if PRESIDIO_AVAILABLE:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            logger.info("Presidio PII detector initialized")
        else:
            self.analyzer = None
            self.anonymizer = None
            logger.warning("Presidio not available, using fallback PII detection")
    
    def scan(self, text: str) -> List[PIIFinding]:
        """
        Detect PII entities in text.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            List of PIIFinding objects
        """
        if not text:
            return []
        
        if PRESIDIO_AVAILABLE and self.analyzer:
            try:
                results = self.analyzer.analyze(
                    text=text,
                    entities=self.PII_ENTITIES,
                    language='en'
                )
                return [PIIFinding.from_presidio(r) for r in results]
            except Exception as e:
                logger.error(f"Presidio analysis failed: {e}")
                return self._fallback_scan(text)
        else:
            return self._fallback_scan(text)
    
    def _fallback_scan(self, text: str) -> List[PIIFinding]:
        """
        Simple regex-based PII detection as fallback.
        
        Args:
            text: Text to scan
            
        Returns:
            List of PIIFinding objects
        """
        import re
        findings = []
        
        # Email detection
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            findings.append(PIIFinding(
                entity_type="EMAIL_ADDRESS",
                text=match.group(),
                start=match.start(),
                end=match.end(),
                score=0.9,
                redacted=False
            ))
        
        # Phone number detection (simple US format)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        for match in re.finditer(phone_pattern, text):
            findings.append(PIIFinding(
                entity_type="PHONE_NUMBER",
                text=match.group(),
                start=match.start(),
                end=match.end(),
                score=0.8,
                redacted=False
            ))
        
        return findings
    
    def redact(self, text: str) -> str:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            
        Returns:
            Text with PII replaced by [REDACTED_TYPE]
        """
        if not text:
            return text
        
        if PRESIDIO_AVAILABLE and self.anonymizer:
            try:
                results = self.analyzer.analyze(
                    text=text,
                    entities=self.PII_ENTITIES,
                    language='en'
                )
                
                anonymized = self.anonymizer.anonymize(
                    text=text,
                    analyzer_results=results
                )
                
                return anonymized.text
            except Exception as e:
                logger.error(f"Presidio anonymization failed: {e}")
                return self._fallback_redact(text)
        else:
            return self._fallback_redact(text)
    
    def _fallback_redact(self, text: str) -> str:
        """
        Simple regex-based redaction as fallback.
        
        Args:
            text: Text to redact
            
        Returns:
            Redacted text
        """
        import re
        
        # Redact emails
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[REDACTED_EMAIL]',
            text
        )
        
        # Redact phone numbers
        text = re.sub(
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            '[REDACTED_PHONE]',
            text
        )
        
        return text
    
    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact PII from dictionary values.
        
        Args:
            data: Dictionary with potential PII
            
        Returns:
            Dictionary with PII redacted
        """
        redacted = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self.redact(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self.redact(item) if isinstance(item, str) else item
                    for item in value
                ]
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            else:
                redacted[key] = value
        
        return redacted
