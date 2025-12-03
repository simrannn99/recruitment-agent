"""
Output validation using Guardrails AI and Pydantic.
"""

from typing import Dict, Any, Optional
import logging
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.guardrails.models import ValidationResult

logger = logging.getLogger(__name__)


class ScreeningResponseSchema(BaseModel):
    """
    Validated schema for screening response.
    
    Ensures all LLM outputs conform to expected structure.
    """
    match_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Match score must be 0-100"
    )
    summary: str = Field(
        ...,
        min_length=50,
        max_length=1000,
        description="Summary must be 50-1000 characters"
    )
    missing_skills: list = Field(
        default_factory=list,
        max_length=15,
        description="Max 15 missing skills"
    )
    interview_questions: list = Field(
        default_factory=list,
        min_length=3,
        max_length=10,
        description="3-10 interview questions required"
    )
    
    @field_validator('missing_skills')
    @classmethod
    def validate_skills(cls, v):
        """Validate missing skills are strings."""
        if not all(isinstance(skill, str) for skill in v):
            raise ValueError("All missing skills must be strings")
        return v
    
    @field_validator('interview_questions')
    @classmethod
    def validate_questions(cls, v):
        """Validate interview questions are strings."""
        if not all(isinstance(q, str) for q in v):
            raise ValueError("All interview questions must be strings")
        
        # Check minimum question length
        for q in v:
            if len(q) < 10:
                raise ValueError(f"Question too short: {q}")
        
        return v


class MultiAgentAnalysisSchema(BaseModel):
    """
    Validated schema for multi-agent analysis response.
    """
    match_score: int = Field(..., ge=0, le=100)
    summary: str = Field(..., min_length=50, max_length=1000)
    missing_skills: list = Field(default_factory=list)
    interview_questions: list = Field(default_factory=list, min_length=3)
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class OutputValidator:
    """
    Validate LLM outputs against defined schemas.
    
    Uses Pydantic for structure validation and custom rules
    for content validation.
    """
    
    def __init__(self):
        """Initialize output validator."""
        self.schemas = {
            'screening': ScreeningResponseSchema,
            'multi_agent': MultiAgentAnalysisSchema
        }
    
    def validate(
        self,
        output: Dict[str, Any],
        schema_name: str = 'screening'
    ) -> ValidationResult:
        """
        Validate output against schema.
        
        Args:
            output: Output dictionary to validate
            schema_name: Name of schema to use ('screening' or 'multi_agent')
            
        Returns:
            ValidationResult object
        """
        schema = self.schemas.get(schema_name)
        
        if not schema:
            return ValidationResult(
                is_valid=False,
                validated_output=None,
                errors=[f"Unknown schema: {schema_name}"]
            )
        
        try:
            # Validate with Pydantic
            validated = schema(**output)
            
            # Additional content validation
            content_errors = self._validate_content(output)
            
            if content_errors:
                return ValidationResult(
                    is_valid=False,
                    validated_output=validated.model_dump(),
                    errors=content_errors
                )
            
            return ValidationResult(
                is_valid=True,
                validated_output=validated.model_dump(),
                errors=[]
            )
        
        except ValidationError as e:
            errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            return ValidationResult(
                is_valid=False,
                validated_output=None,
                errors=errors
            )
        
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validated_output=None,
                errors=[f"Validation error: {str(e)}"]
            )
    
    def _validate_content(self, output: Dict[str, Any]) -> list:
        """
        Validate content quality beyond structure.
        
        Args:
            output: Output to validate
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check summary quality
        summary = output.get('summary', '')
        if summary:
            # Check for placeholder text
            placeholders = ['lorem ipsum', 'todo', 'tbd', 'xxx', 'placeholder']
            if any(p in summary.lower() for p in placeholders):
                errors.append("Summary contains placeholder text")
            
            # Check for repetition
            words = summary.lower().split()
            if len(words) != len(set(words)):
                word_counts = {}
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1
                
                repeated = [w for w, c in word_counts.items() if c > 3 and len(w) > 3]
                if repeated:
                    errors.append(f"Summary has excessive repetition: {repeated[:3]}")
        
        # Check interview questions quality
        questions = output.get('interview_questions', [])
        if questions:
            # Check for duplicate questions
            if len(questions) != len(set(questions)):
                errors.append("Duplicate interview questions detected")
            
            # Check for generic questions
            generic_questions = [
                "tell me about yourself",
                "what are your strengths",
                "what are your weaknesses",
                "where do you see yourself in 5 years"
            ]
            
            for q in questions:
                if any(generic in q.lower() for generic in generic_questions):
                    errors.append(f"Generic interview question: {q[:50]}...")
        
        # Check missing skills
        skills = output.get('missing_skills', [])
        if len(skills) > 15:
            errors.append(f"Too many missing skills ({len(skills)}), limit to 15")
        
        return errors
    
    def validate_and_fix(
        self,
        output: Dict[str, Any],
        schema_name: str = 'screening'
    ) -> Dict[str, Any]:
        """
        Validate output and attempt to fix common issues.
        
        Args:
            output: Output to validate
            schema_name: Schema to use
            
        Returns:
            Fixed output dictionary
        """
        # Try validation first
        result = self.validate(output, schema_name)
        
        if result.is_valid:
            return result.validated_output
        
        # Attempt fixes
        fixed = output.copy()
        
        # Fix match_score range
        if 'match_score' in fixed:
            score = fixed['match_score']
            if score < 0:
                fixed['match_score'] = 0
            elif score > 100:
                fixed['match_score'] = 100
        
        # Fix summary length
        if 'summary' in fixed:
            summary = fixed['summary']
            if len(summary) < 50:
                fixed['summary'] = summary + " " + "This candidate shows potential for the role."
            elif len(summary) > 1000:
                fixed['summary'] = summary[:997] + "..."
        
        # Fix interview questions count
        if 'interview_questions' in fixed:
            questions = fixed['interview_questions']
            if len(questions) < 3:
                # Add generic questions to meet minimum
                while len(questions) < 3:
                    questions.append(f"Question {len(questions) + 1}: Please elaborate on your experience.")
            elif len(questions) > 10:
                fixed['interview_questions'] = questions[:10]
        
        # Try validation again
        result = self.validate(fixed, schema_name)
        
        if result.is_valid:
            logger.info("Successfully fixed validation errors")
            return result.validated_output
        else:
            logger.warning(f"Could not fix all validation errors: {result.errors}")
            return fixed
