"""
Main safety guardrails orchestrator.

Coordinates all safety checks for AI-generated content.
"""

from typing import Dict, Any, Optional
import logging

from app.guardrails.models import SafetyReport
from app.guardrails.pii_detector import PIIDetector
from app.guardrails.bias_detector import BiasDetector
from app.guardrails.toxicity_filter import ToxicityFilter
from app.guardrails.output_validator import OutputValidator

logger = logging.getLogger(__name__)


class SafetyGuardrails:
    """
    Orchestrate all safety checks for LLM outputs.
    
    Performs:
    1. PII detection and redaction
    2. Bias detection
    3. Toxicity filtering
    4. Output validation
    """
    
    def __init__(
        self,
        pii_mode: str = "flag",
        use_llm_bias: bool = False,
        llm=None,
        toxicity_threshold: float = 0.7
    ):
        """
        Initialize safety guardrails.
        
        Args:
            pii_mode: "flag" or "redact" for PII handling
            use_llm_bias: Whether to use LLM for implicit bias detection
            llm: Language model for bias detection
            toxicity_threshold: Threshold for toxicity (0-1)
        """
        self.pii_detector = PIIDetector(mode=pii_mode)
        self.bias_detector = BiasDetector(use_llm=use_llm_bias, llm=llm)
        self.toxicity_filter = ToxicityFilter(threshold=toxicity_threshold)
        self.output_validator = OutputValidator()
        
        logger.info(f"SafetyGuardrails initialized (PII mode: {pii_mode})")
    
    def validate_analysis(
        self,
        analysis: Dict[str, Any],
        schema_name: str = 'screening'
    ) -> SafetyReport:
        """
        Run all safety checks on AI analysis.
        
        Args:
            analysis: Analysis dictionary to check
            schema_name: Schema to validate against
            
        Returns:
            SafetyReport with all findings
        """
        report = SafetyReport()
        
        try:
            # 1. Check for PII leakage
            pii_findings = self._check_pii(analysis)
            report.add_pii_findings(pii_findings)
            
            # 2. Check for bias
            bias_findings = self.bias_detector.scan(analysis)
            report.add_bias_findings(bias_findings)
            
            # 3. Check for toxicity
            toxicity_score = self._check_toxicity(analysis)
            if toxicity_score:
                report.add_toxicity_score(toxicity_score)
            
            # 4. Validate structure and content
            validation_result = self.output_validator.validate(
                analysis,
                schema_name=schema_name
            )
            report.add_validation_results(validation_result)
            
            logger.info(f"Safety check complete: {report.summary()}")
            
        except Exception as e:
            logger.error(f"Safety validation failed: {e}")
            # Don't fail the entire analysis, just log the error
        
        return report
    
    def _check_pii(self, analysis: Dict[str, Any]) -> list:
        """
        Check all string fields for PII.
        
        Args:
            analysis: Analysis to check
            
        Returns:
            List of PIIFinding objects
        """
        findings = []
        
        # Check summary
        if 'summary' in analysis:
            findings.extend(self.pii_detector.scan(analysis['summary']))
        
        # Check missing skills
        if 'missing_skills' in analysis:
            for skill in analysis['missing_skills']:
                if isinstance(skill, str):
                    findings.extend(self.pii_detector.scan(skill))
        
        # Check interview questions
        if 'interview_questions' in analysis:
            for question in analysis['interview_questions']:
                if isinstance(question, str):
                    findings.extend(self.pii_detector.scan(question))
        
        return findings
    
    def _check_toxicity(self, analysis: Dict[str, Any]):
        """
        Check all string fields for toxicity.
        
        Args:
            analysis: Analysis to check
            
        Returns:
            ToxicityScore or None
        """
        # Combine all text for toxicity check
        text_parts = []
        
        if 'summary' in analysis:
            text_parts.append(str(analysis['summary']))
        
        if 'missing_skills' in analysis:
            text_parts.extend([str(s) for s in analysis['missing_skills']])
        
        if 'interview_questions' in analysis:
            text_parts.extend([str(q) for q in analysis['interview_questions']])
        
        combined_text = " ".join(text_parts)
        
        return self.toxicity_filter.score(combined_text)
    
    def redact_pii(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact PII from analysis.
        
        Args:
            analysis: Analysis to redact
            
        Returns:
            Redacted analysis
        """
        return self.pii_detector.redact_dict(analysis)
    
    def validate_and_sanitize(
        self,
        analysis: Dict[str, Any],
        schema_name: str = 'screening',
        auto_redact: bool = True
    ) -> tuple[Dict[str, Any], SafetyReport]:
        """
        Validate analysis and sanitize if needed.
        
        Args:
            analysis: Analysis to validate
            schema_name: Schema to use
            auto_redact: Whether to automatically redact PII
            
        Returns:
            Tuple of (sanitized_analysis, safety_report)
        """
        # Run safety checks
        report = self.validate_analysis(analysis, schema_name)
        
        # Sanitize if needed
        sanitized = analysis.copy()
        
        if auto_redact and report.pii_findings:
            sanitized = self.redact_pii(sanitized)
            logger.info(f"Redacted {len(report.pii_findings)} PII entities")
        
        # Fix validation errors if possible
        if report.validation_result and not report.validation_result.is_valid:
            sanitized = self.output_validator.validate_and_fix(
                sanitized,
                schema_name
            )
            logger.info("Applied automatic fixes to validation errors")
        
        return sanitized, report
