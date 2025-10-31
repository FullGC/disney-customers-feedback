from __future__ import annotations

import logging
from typing import Any

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize the embedding service.
        
        Args:
            model_name: The sentence transformer model to use.
        """
        self.model_name = model_name
        self.model: SentenceTransformer | None = None
        
    def load_model(self) -> None:
        """Load the sentence transformer model."""
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        logger.info("Embedding model loaded successfully")
        
    def embed_text(self, text: str) -> list[float]:
        """Generate embeddings for a single text.
        
        Args:
            text: The text to embed.
            
        Returns:
            List of float values representing the embedding.
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
            
        # Clean and prepare text
        clean_text = str(text).strip()
        if not clean_text:
            clean_text = "No content"
            
        # Generate embedding
        embedding = self.model.encode([clean_text])[0]
        return embedding.tolist()
        
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed.
            
        Returns:
            List of embeddings, each as a list of floats.
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
            
        # Clean and prepare texts
        clean_texts = []
        for text in texts:
            clean_text = str(text).strip()
            if not clean_text:
                clean_text = "No content"
            clean_texts.append(clean_text)
            
        logger.info(f"Generating embeddings for {len(clean_texts)} texts")
        
        # Generate embeddings in batch
        embeddings = self.model.encode(clean_texts)
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        return [embedding.tolist() for embedding in embeddings]