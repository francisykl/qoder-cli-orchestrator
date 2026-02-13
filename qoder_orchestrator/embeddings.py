#!/usr/bin/env python3
"""
Semantic search using embeddings for wiki and skills content.
Enables intelligent context retrieval based on task similarity.
"""

import os
import pickle
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages embeddings for semantic search."""
    
    def __init__(self, config: Any, cache_dir: Optional[Path] = None):
        """
        Initialize embedding manager.
        
        Args:
            config: SemanticSearchConfig instance
            cache_dir: Directory for caching embeddings
        """
        self.config = config
        self.cache_dir = cache_dir or Path(".qoder-cache/embeddings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.embeddings_cache: Dict[str, np.ndarray] = {}
        
        if config.enabled:
            self._load_model()
            if config.cache_embeddings:
                self._load_cache()
    
    def _load_model(self):
        """Load sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {self.config.model_name}")
            self.model = SentenceTransformer(self.config.model_name)
            logger.info("✓ Embedding model loaded")
            
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            self.config.enabled = False
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.config.enabled = False
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _load_cache(self):
        """Load cached embeddings from disk."""
        cache_file = self.cache_dir / "embeddings.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    self.embeddings_cache = pickle.load(f)
                logger.info(f"Loaded {len(self.embeddings_cache)} cached embeddings")
            except Exception as e:
                logger.warning(f"Failed to load embedding cache: {e}")
                self.embeddings_cache = {}
    
    def _save_cache(self):
        """Save embeddings cache to disk."""
        if not self.config.cache_embeddings:
            return
        
        cache_file = self.cache_dir / "embeddings.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self.embeddings_cache, f)
            logger.debug(f"Saved {len(self.embeddings_cache)} embeddings to cache")
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")
    
    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        if not self.config.enabled or not self.model:
            return None
        
        # Check cache
        cache_key = self._get_cache_key(text)
        if cache_key in self.embeddings_cache:
            return self.embeddings_cache[cache_key]
        
        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Cache it
            if self.config.cache_embeddings:
                self.embeddings_cache[cache_key] = embedding
                self._save_cache()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def embed_documents(self, documents: Dict[str, str]) -> Dict[str, np.ndarray]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            documents: Dictionary of {name: content}
            
        Returns:
            Dictionary of {name: embedding}
        """
        embeddings = {}
        
        for name, content in documents.items():
            embedding = self.embed_text(content)
            if embedding is not None:
                embeddings[name] = embedding
        
        return embeddings
    
    def find_similar(
        self,
        query: str,
        documents: Dict[str, str],
        top_k: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """
        Find documents similar to query.
        
        Args:
            query: Query text
            documents: Dictionary of {name: content}
            top_k: Number of results to return (default: config.max_results)
            
        Returns:
            List of (document_name, similarity_score) tuples, sorted by similarity
        """
        if not self.config.enabled:
            # Fallback to keyword matching
            return self._keyword_fallback(query, documents, top_k)
        
        top_k = top_k or self.config.max_results
        
        # Embed query
        query_embedding = self.embed_text(query)
        if query_embedding is None:
            return self._keyword_fallback(query, documents, top_k)
        
        # Embed documents
        doc_embeddings = self.embed_documents(documents)
        
        # Calculate similarities
        similarities = []
        for name, doc_embedding in doc_embeddings.items():
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            
            # Filter by threshold
            if similarity >= self.config.similarity_threshold:
                similarities.append((name, float(similarity)))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k
        return similarities[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _keyword_fallback(
        self,
        query: str,
        documents: Dict[str, str],
        top_k: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """
        Fallback to simple keyword matching when embeddings unavailable.
        
        Args:
            query: Query text
            documents: Dictionary of {name: content}
            top_k: Number of results to return
            
        Returns:
            List of (document_name, score) tuples
        """
        top_k = top_k or self.config.max_results
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scores = []
        for name, content in documents.items():
            content_lower = content.lower()
            content_words = set(content_lower.split())
            
            # Calculate word overlap
            overlap = len(query_words & content_words)
            
            # Also check if query is substring
            substring_bonus = 0.5 if query_lower in content_lower else 0
            
            score = overlap + substring_bonus
            
            if score > 0:
                scores.append((name, score))
        
        # Normalize scores
        if scores:
            max_score = max(s[1] for s in scores)
            scores = [(name, score / max_score) for name, score in scores]
        
        # Sort and return top k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def clear_cache(self):
        """Clear embeddings cache."""
        self.embeddings_cache = {}
        cache_file = self.cache_dir / "embeddings.pkl"
        if cache_file.exists():
            cache_file.unlink()
        logger.info("Embedding cache cleared")


def create_embedding_manager(config: Any, cache_dir: Optional[Path] = None) -> EmbeddingManager:
    """
    Factory function to create embedding manager.
    
    Args:
        config: SemanticSearchConfig instance
        cache_dir: Optional cache directory
        
    Returns:
        EmbeddingManager instance
    """
    return EmbeddingManager(config, cache_dir)
