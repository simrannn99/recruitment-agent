"""
Embedding service for generating vector embeddings from text.

Supports multiple providers:
- sentence-transformers (local, free)
- OpenAI (cloud, paid)
"""
import os
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings from text using various providers."""
    
    def __init__(self):
        """Initialize the embedding service with the configured provider."""
        self.provider = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers").lower()
        self.model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        if self.provider == "sentence-transformers":
            self._init_sentence_transformers()
        elif self.provider == "openai":
            self._init_openai()
        else:
            raise ValueError(
                f"Unsupported embedding provider: {self.provider}. "
                "Use 'sentence-transformers' or 'openai'"
            )
        
        logger.info(f"✓ Initialized EmbeddingService with provider: {self.provider}, model: {self.model_name}")
    
    def _init_sentence_transformers(self):
        """Initialize sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded sentence-transformers model: {self.model_name} ({self.dimension} dimensions)")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
    
    def _init_openai(self):
        """Initialize OpenAI embeddings."""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
            
            self.client = OpenAI(api_key=api_key)
            # OpenAI text-embedding-3-small has 1536 dimensions
            # text-embedding-ada-002 has 1536 dimensions
            self.dimension = 1536 if "3" in self.model_name else 1536
            logger.info(f"Initialized OpenAI embeddings: {self.model_name} ({self.dimension} dimensions)")
        except ImportError:
            raise ImportError(
                "openai not installed. "
                "Install with: pip install openai"
            )
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector from text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector, or None if text is empty
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return None
        
        try:
            if self.provider == "sentence-transformers":
                return self._generate_sentence_transformers(text)
            elif self.provider == "openai":
                return self._generate_openai(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def _generate_sentence_transformers(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def _generate_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text
        )
        return response.data[0].embedding
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (same order as input)
        """
        if not texts:
            return []
        
        try:
            if self.provider == "sentence-transformers":
                return self._generate_batch_sentence_transformers(texts)
            elif self.provider == "openai":
                return self._generate_batch_openai(texts)
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def _generate_batch_sentence_transformers(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate batch embeddings using sentence-transformers."""
        # Filter out empty texts but keep track of indices
        valid_texts = [(i, text) for i, text in enumerate(texts) if text and text.strip()]
        
        if not valid_texts:
            return [None] * len(texts)
        
        indices, valid_text_list = zip(*valid_texts)
        embeddings = self.model.encode(list(valid_text_list), convert_to_numpy=True)
        
        # Reconstruct result list with None for empty texts
        result = [None] * len(texts)
        for idx, embedding in zip(indices, embeddings):
            result[idx] = embedding.tolist()
        
        return result
    
    def _generate_batch_openai(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate batch embeddings using OpenAI API."""
        # Filter out empty texts
        valid_texts = [(i, text) for i, text in enumerate(texts) if text and text.strip()]
        
        if not valid_texts:
            return [None] * len(texts)
        
        indices, valid_text_list = zip(*valid_texts)
        
        response = self.client.embeddings.create(
            model=self.model_name,
            input=list(valid_text_list)
        )
        
        # Reconstruct result list
        result = [None] * len(texts)
        for idx, embedding_obj in zip(indices, response.data):
            result[idx] = embedding_obj.embedding
        
        return result
    
    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service."""
        return self.dimension
