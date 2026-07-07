import logging

logger = logging.getLogger(__name__)

_SPACY_MODEL = None
_SENTENCE_TRANSFORMER_MODEL = None

def get_spacy_model():
    global _SPACY_MODEL
    if _SPACY_MODEL is None:
        try:
            import spacy
            _SPACY_MODEL = spacy.load("en_core_web_sm")
            logger.info("Loaded spaCy model.")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}")
            _SPACY_MODEL = None
    else:
        logger.info("Using cached spaCy model.")
    return _SPACY_MODEL

def get_sentence_transformer_model():
    global _SENTENCE_TRANSFORMER_MODEL
    if _SENTENCE_TRANSFORMER_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Hardcoded to "all-MiniLM-L6-v2" to match semantic_matcher.py
            _SENTENCE_TRANSFORMER_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded SentenceTransformer model.")
        except Exception as e:
            logger.warning(f"Failed to load SentenceTransformer model: {e}")
            _SENTENCE_TRANSFORMER_MODEL = None
    else:
        logger.info("Using cached SentenceTransformer model.")
    return _SENTENCE_TRANSFORMER_MODEL
