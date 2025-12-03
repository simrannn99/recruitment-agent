"""
Bias detection for recruitment analysis.
"""

from typing import List, Dict, Optional
import logging
import re

from app.guardrails.models import BiasFinding

logger = logging.getLogger(__name__)


class BiasDetector:
    """
    Detect potential bias in recruitment analysis.
    
    Checks for bias related to:
    - Age
    - Gender
    - Race/Ethnicity
    - Disability
    - Religion
    """
    
    PROTECTED_ATTRIBUTES = {
        "age": {
            "keywords": [
                "young", "old", "recent graduate", "experienced professional",
                "senior", "junior", "mature", "youthful", "energetic",
                "fresh", "seasoned", "veteran", "new grad", "entry-level"
            ],
            "severity": "medium"
        },
        "gender": {
            "keywords": [
                "he", "she", "him", "her", "his", "hers",
                "guy", "gal", "man", "woman", "male", "female",
                "gentleman", "lady", "boy", "girl"
            ],
            "severity": "high"
        },
        "disability": {
            "keywords": [
                "disabled", "handicapped", "able-bodied", "wheelchair",
                "blind", "deaf", "impaired", "special needs"
            ],
            "severity": "high"
        },
        "religion": {
            "keywords": [
                "christian", "muslim", "jewish", "hindu", "buddhist",
                "catholic", "protestant", "atheist", "religious"
            ],
            "severity": "high"
        },
        "appearance": {
            "keywords": [
                "attractive", "beautiful", "handsome", "ugly",
                "overweight", "thin", "tall", "short"
            ],
            "severity": "high"
        }
    }
    
    def __init__(self, use_llm: bool = False, llm=None):
        """
        Initialize bias detector.
        
        Args:
            use_llm: Whether to use LLM for implicit bias detection
            llm: Language model for implicit bias detection
        """
        self.use_llm = use_llm
        self.llm = llm
        
        if use_llm and not llm:
            logger.warning("LLM-based bias detection requested but no LLM provided")
            self.use_llm = False
    
    def scan(self, analysis: Dict) -> List[BiasFinding]:
        """
        Detect potential bias in analysis.
        
        Args:
            analysis: Analysis dictionary to check
            
        Returns:
            List of BiasFinding objects
        """
        findings = []
        
        # Extract text to analyze
        text_parts = []
        if isinstance(analysis, dict):
            text_parts.append(analysis.get('summary', ''))
            
            # Check missing_skills
            missing_skills = analysis.get('missing_skills', [])
            if isinstance(missing_skills, list):
                text_parts.extend(missing_skills)
            
            # Check interview questions
            questions = analysis.get('interview_questions', [])
            if isinstance(questions, list):
                text_parts.extend(questions)
        
        text = " ".join(str(part) for part in text_parts)
        
        # Keyword-based detection
        findings.extend(self._keyword_scan(text))
        
        # LLM-based implicit bias detection
        if self.use_llm:
            findings.extend(self._llm_scan(text))
        
        return findings
    
    def _keyword_scan(self, text: str) -> List[BiasFinding]:
        """
        Scan for bias using keyword matching.
        
        Args:
            text: Text to scan
            
        Returns:
            List of BiasFinding objects
        """
        findings = []
        text_lower = text.lower()
        
        for category, config in self.PROTECTED_ATTRIBUTES.items():
            keywords = config["keywords"]
            severity = config["severity"]
            
            for keyword in keywords:
                # Use word boundaries to avoid false positives
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = list(re.finditer(pattern, text_lower))
                
                for match in matches:
                    # Extract context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]
                    
                    findings.append(BiasFinding(
                        category=category,
                        keyword=keyword,
                        context=context,
                        severity=severity,
                        explanation=f"Detected '{keyword}' which may indicate {category} bias"
                    ))
        
        return findings
    
    def _llm_scan(self, text: str) -> List[BiasFinding]:
        """
        Use LLM to detect implicit bias.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of BiasFinding objects
        """
        if not self.llm:
            return []
        
        try:
            prompt = f"""Analyze this recruitment feedback for potential bias:

{text}

Look for:
1. Age bias (preferring younger/older candidates, using age-related language)
2. Gender bias (gendered language, assumptions about gender)
3. Cultural bias (assumptions about background, nationality, ethnicity)
4. Disability bias (assumptions about physical or mental capabilities)
5. Appearance bias (comments on physical appearance)

For each bias found, respond with JSON:
{{
    "bias_detected": true/false,
    "category": "age/gender/race/disability/appearance",
    "explanation": "Brief explanation of the bias",
    "severity": "low/medium/high"
}}

If no bias detected, return: {{"bias_detected": false}}
"""
            
            response = self.llm.invoke(prompt)
            
            # Parse LLM response
            import json
            try:
                result = json.loads(response.content)
                
                if result.get("bias_detected"):
                    return [BiasFinding(
                        category=result.get("category", "unknown"),
                        keyword=None,
                        context=text[:200],  # First 200 chars as context
                        severity=result.get("severity", "medium"),
                        explanation=result.get("explanation", "LLM detected potential bias")
                    )]
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM bias detection response")
        
        except Exception as e:
            logger.error(f"LLM bias detection failed: {e}")
        
        return []
    
    def check_for_positive_bias(self, analysis: Dict) -> List[BiasFinding]:
        """
        Check for positive bias (unfairly favoring certain groups).
        
        Args:
            analysis: Analysis to check
            
        Returns:
            List of BiasFinding objects
        """
        findings = []
        
        # Check for diversity-related positive bias
        text = str(analysis.get('summary', ''))
        
        positive_bias_keywords = [
            "diversity hire", "minority candidate", "underrepresented",
            "affirmative action", "quota"
        ]
        
        for keyword in positive_bias_keywords:
            if keyword.lower() in text.lower():
                findings.append(BiasFinding(
                    category="positive_bias",
                    keyword=keyword,
                    context=text[:200],
                    severity="medium",
                    explanation=f"Detected '{keyword}' which may indicate positive discrimination"
                ))
        
        return findings
