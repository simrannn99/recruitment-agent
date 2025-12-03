"""
Toxicity filtering using Detoxify model.
"""

from typing import Optional
import logging

try:
    from detoxify import Detoxify
    DETOXIFY_AVAILABLE = True
except ImportError:
    DETOXIFY_AVAILABLE = False
    logging.warning("Detoxify not installed. Toxicity filtering will be disabled.")

from app.guardrails.models import ToxicityScore

logger = logging.getLogger(__name__)


class ToxicityFilter:
    """
    Detect toxic language in LLM outputs using Detoxify.
    
    Detects:
    - General toxicity
    - Severe toxicity
    - Obscene language
    - Threats
    - Insults
    - Identity attacks
    """
    
    TOXICITY_THRESHOLD = 0.7  # 0-1 scale
    
    def __init__(self, threshold: float = 0.7):
        """
        Initialize toxicity filter.
        
        Args:
            threshold: Toxicity threshold (0-1). Content above this is flagged.
        """
        self.threshold = threshold
        
        if DETOXIFY_AVAILABLE:
            try:
                self.model = Detoxify('original')
                logger.info("Detoxify model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Detoxify model: {e}")
                self.model = None
        else:
            self.model = None
            logger.warning("Detoxify not available, toxicity filtering disabled")
    
    def score(self, text: str) -> Optional[ToxicityScore]:
        """
        Score text for toxicity.
        
        Args:
            text: Text to analyze
            
        Returns:
            ToxicityScore object or None if model unavailable
        """
        if not text:
            return None
        
        if not self.model:
            # Return neutral scores if model not available
            return ToxicityScore(
                toxicity=0.0,
                severe_toxicity=0.0,
                obscene=0.0,
                threat=0.0,
                insult=0.0,
                identity_attack=0.0,
                is_toxic=False
            )
        
        try:
            results = self.model.predict(text)
            
            return ToxicityScore(
                toxicity=float(results['toxicity']),
                severe_toxicity=float(results['severe_toxicity']),
                obscene=float(results['obscene']),
                threat=float(results['threat']),
                insult=float(results['insult']),
                identity_attack=float(results['identity_attack']),
                is_toxic=float(results['toxicity']) > self.threshold
            )
        
        except Exception as e:
            logger.error(f"Toxicity scoring failed: {e}")
            return None
    
    def filter(self, text: str) -> str:
        """
        Return text only if non-toxic, else raise error.
        
        Args:
            text: Text to filter
            
        Returns:
            Original text if non-toxic
            
        Raises:
            ToxicContentError: If content is toxic
        """
        score = self.score(text)
        
        if score and score.is_toxic:
            raise ToxicContentError(
                f"Toxic content detected (score: {score.toxicity:.2f})"
            )
        
        return text
    
    def score_dict(self, data: dict) -> dict:
        """
        Score all string values in a dictionary.
        
        Args:
            data: Dictionary to score
            
        Returns:
            Dictionary mapping keys to toxicity scores
        """
        scores = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                score = self.score(value)
                if score:
                    scores[key] = score
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        score = self.score(item)
                        if score:
                            scores[f"{key}[{i}]"] = score
        
        return scores


class ToxicContentError(Exception):
    """Raised when toxic content is detected."""
    pass
