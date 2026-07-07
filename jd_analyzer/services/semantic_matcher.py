"""
Semantic Matching Service
Uses sentence-transformers (all-MiniLM-L6-v2) + cosine similarity
to compute semantic overlap between JD and resume beyond exact keyword matching.

Compares:
  - JD skill phrases vs Resume skill phrases
  - JD requirements vs Resume project/experience text

Caches embeddings to avoid redundant computation.
"""

import hashlib
import logging
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticMatcherService:
    """
    Sentence-transformer-based semantic similarity scorer.
    Falls back to TF-IDF cosine similarity if transformers are unavailable.
    """

    def __init__(self):
        self._model = self._load_model()
        self._embedding_cache: Dict[str, np.ndarray] = {}

    @staticmethod
    def _load_model():
        import os
        use_transformer = os.getenv("USE_SENTENCE_TRANSFORMER", "false").lower() in ("true", "1", "yes")
        
        if not use_transformer:
            logger.info("[JD] Semantic matcher using deterministic TF-IDF backend")
            return None
            
        try:
            from .model_cache import get_sentence_transformer_model
            model = get_sentence_transformer_model()
            if model:
                logger.info("[JD] Semantic matcher using SentenceTransformer backend")
                return model
            else:
                logger.warning("[SemanticMatcher] SentenceTransformer unavailable. Using TF-IDF fallback.")
                return None
        except Exception as e:
            logger.warning(f"[SemanticMatcher] Model load failed: {e}. Using TF-IDF fallback.")
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_similarity(
        self,
        jd_text: str,
        resume_text: str,
        jd_skills: List[str],
        resume_skills: List[str],
    ) -> Dict[str, float]:
        """
        Compute semantic similarity scores.

        Returns:
            {
              "skill_semantic_score": float (0-100),
              "text_semantic_score": float (0-100),
              "overall_semantic_score": float (0-100),
              "method": "transformers" | "tfidf"
            }
        """
        if self._model:
            return self._transformer_similarity(
                jd_text, resume_text, jd_skills, resume_skills
            )
        else:
            return self._tfidf_similarity(jd_text, resume_text)

    # ------------------------------------------------------------------
    # Transformer-based similarity
    # ------------------------------------------------------------------

    def _transformer_similarity(
        self,
        jd_text: str,
        resume_text: str,
        jd_skills: List[str],
        resume_skills: List[str],
    ) -> Dict[str, float]:
        """Use sentence-transformers for embedding-based similarity."""

        # 1. Skill-level semantic similarity
        skill_score = 0.0
        if jd_skills and resume_skills:
            jd_skill_embs = self._get_embeddings(jd_skills)
            resume_skill_embs = self._get_embeddings(resume_skills)
            skill_score = self._max_cosine_similarity(jd_skill_embs, resume_skill_embs)

        # 2. Full-text semantic similarity (chunked)
        text_score = 0.0
        if jd_text and resume_text:
            jd_chunks = self._chunk_text(jd_text)
            resume_chunks = self._chunk_text(resume_text)
            jd_embs = self._get_embeddings(jd_chunks)
            resume_embs = self._get_embeddings(resume_chunks)
            text_score = self._max_cosine_similarity(jd_embs, resume_embs)

        # 3. Combined score (skill-heavy weighting)
        overall = (skill_score * 0.6 + text_score * 0.4) * 100

        return {
            "skill_semantic_score": round(skill_score * 100, 2),
            "text_semantic_score": round(text_score * 100, 2),
            "overall_semantic_score": round(overall, 2),
            "method": "transformers",
        }

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Return embeddings, using cache to avoid recomputing."""
        cache_key = hashlib.md5("|".join(texts).encode()).hexdigest()
        if cache_key not in self._embedding_cache:
            try:
                import time
                logger.info("[JD] About to encode embedding")
                t0_emb = time.perf_counter()
                self._embedding_cache[cache_key] = self._model.encode(
                    texts, convert_to_numpy=True, show_progress_bar=False
                )
                logger.info(f"[JD] Embedding complete in {time.perf_counter() - t0_emb:.2f} sec")
            except Exception as e:
                logger.error(f"[JD] Error in SentenceTransformer encoding: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise
        return self._embedding_cache[cache_key]

    @staticmethod
    def _max_cosine_similarity(embs_a: np.ndarray, embs_b: np.ndarray) -> float:
        """
        For each vector in A, find the maximum cosine similarity to any vector in B.
        Returns the mean of those maxima — measures "best-match coverage".
        """
        try:
            import time
            logger.info("[JD] About to compute cosine similarity")
            t0_cos = time.perf_counter()
            # Normalize
            norm_a = embs_a / (np.linalg.norm(embs_a, axis=1, keepdims=True) + 1e-8)
            norm_b = embs_b / (np.linalg.norm(embs_b, axis=1, keepdims=True) + 1e-8)
    
            # Similarity matrix [len_a x len_b]
            sim_matrix = np.dot(norm_a, norm_b.T)
    
            # Max similarity per row (each JD item matched to best resume item)
            max_sims = sim_matrix.max(axis=1)
            result = float(np.mean(max_sims))
            logger.info(f"[JD] Cosine similarity complete in {time.perf_counter() - t0_cos:.2f} sec")
            return result
        except Exception as e:
            logger.error(f"[JD] Error in Similarity calculation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 200, overlap: int = 50) -> List[str]:
        """Split text into overlapping word-chunks for embedding."""
        words = text.split()
        if len(words) <= chunk_size:
            return [text[:5000]]  # single chunk

        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i: i + chunk_size])
            chunks.append(chunk)
            if len(chunks) >= 10:  # cap at 10 chunks
                break
        return chunks

    # ------------------------------------------------------------------
    # TF-IDF fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _tfidf_similarity(jd_text: str, resume_text: str) -> Dict[str, float]:
        """Fallback: cosine similarity using TF-IDF vectors."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
            tfidf_matrix = vectorizer.fit_transform([jd_text, resume_text])
            score = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
            score_pct = round(score * 100, 2)

            return {
                "skill_semantic_score": score_pct,
                "text_semantic_score": score_pct,
                "overall_semantic_score": score_pct,
                "method": "tfidf",
            }
        except ImportError:
            logger.warning("[SemanticMatcher] sklearn not available. Returning 0.")
            return {
                "skill_semantic_score": 0.0,
                "text_semantic_score": 0.0,
                "overall_semantic_score": 0.0,
                "method": "none",
            }
