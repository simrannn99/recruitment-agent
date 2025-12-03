"""
Data models for safety guardrails.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PIIFinding(BaseModel):
    """Represents a detected PII entity."""
    entity_type: str = Field(..., description="Type of PII (EMAIL, PHONE, etc.)")
    text: str = Field(..., description="The actual PII text found")
    start: int = Field(..., description="Start position in text")
    end: int = Field(..., description="End position in text")
    score: float = Field(..., description="Confidence score (0-1)")
    redacted: bool = Field(default=False, description="Whether this was redacted")
    
    @classmethod
    def from_presidio(cls, result):
        """Create from Presidio AnalyzerResult."""
        return cls(
            entity_type=result.entity_type,
            text="",  # Presidio doesn't return original text
            start=result.start,
            end=result.end,
            score=result.score,
            redacted=False
        )


class BiasFinding(BaseModel):
    """Represents a detected bias."""
    category: str = Field(..., description="Bias category (age, gender, race, etc.)")
    keyword: Optional[str] = Field(None, description="Keyword that triggered detection")
    context: str = Field(..., description="Context where bias was found")
    severity: str = Field(..., description="Severity: low, medium, high")
    explanation: Optional[str] = Field(None, description="LLM explanation of bias")


class ToxicityScore(BaseModel):
    """Toxicity scores from Detoxify model."""
    toxicity: float = Field(..., description="Overall toxicity score (0-1)")
    severe_toxicity: float = Field(..., description="Severe toxicity score")
    obscene: float = Field(..., description="Obscenity score")
    threat: float = Field(..., description="Threat score")
    insult: float = Field(..., description="Insult score")
    identity_attack: float = Field(..., description="Identity attack score")
    is_toxic: bool = Field(..., description="Whether content is considered toxic")


class ValidationResult(BaseModel):
    """Result of output validation."""
    is_valid: bool = Field(..., description="Whether output is valid")
    validated_output: Optional[Dict[str, Any]] = Field(None, description="Validated output")
    errors: List[str] = Field(default_factory=list, description="Validation errors")


class SafetyReport(BaseModel):
    """Comprehensive safety report for an analysis."""
    timestamp: datetime = Field(default_factory=datetime.now)
    pii_findings: List[PIIFinding] = Field(default_factory=list)
    bias_findings: List[BiasFinding] = Field(default_factory=list)
    toxicity_score: Optional[ToxicityScore] = None
    validation_result: Optional[ValidationResult] = None
    has_issues: bool = Field(default=False)
    has_critical_issues: bool = Field(default=False)
    
    def add_pii_findings(self, findings: List[PIIFinding]):
        """Add PII findings to report."""
        self.pii_findings.extend(findings)
        if findings:
            self.has_issues = True
    
    def add_bias_findings(self, findings: List[BiasFinding]):
        """Add bias findings to report."""
        self.bias_findings.extend(findings)
        if findings:
            self.has_issues = True
            # Critical if high severity bias detected
            if any(f.severity == "high" for f in findings):
                self.has_critical_issues = True
    
    def add_toxicity_score(self, score: ToxicityScore):
        """Add toxicity score to report."""
        self.toxicity_score = score
        if score.is_toxic:
            self.has_issues = True
            self.has_critical_issues = True
    
    def add_validation_results(self, result: ValidationResult):
        """Add validation results to report."""
        self.validation_result = result
        if not result.is_valid:
            self.has_issues = True
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        parts = []
        
        if self.pii_findings:
            parts.append(f"{len(self.pii_findings)} PII entities detected")
        
        if self.bias_findings:
            parts.append(f"{len(self.bias_findings)} potential bias issues")
        
        if self.toxicity_score and self.toxicity_score.is_toxic:
            parts.append(f"Toxic content detected (score: {self.toxicity_score.toxicity:.2f})")
        
        if self.validation_result and not self.validation_result.is_valid:
            parts.append(f"{len(self.validation_result.errors)} validation errors")
        
        if not parts:
            return "No safety issues detected"
        
        return "; ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "pii_findings": [f.model_dump() for f in self.pii_findings],
            "bias_findings": [f.model_dump() for f in self.bias_findings],
            "toxicity_score": self.toxicity_score.model_dump() if self.toxicity_score else None,
            "validation_result": self.validation_result.model_dump() if self.validation_result else None,
            "has_issues": self.has_issues,
            "has_critical_issues": self.has_critical_issues,
            "summary": self.summary()
        }
