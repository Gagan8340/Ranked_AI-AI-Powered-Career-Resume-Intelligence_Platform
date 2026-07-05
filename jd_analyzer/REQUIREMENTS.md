# ── JD Analyzer — Python Dependencies ──────────────────────────────────────
# Core (required)
flask>=2.3.0
werkzeug>=2.3.0

# File Parsing
pymupdf>=1.23.0          # PDF parsing (fitz)
python-docx>=1.1.0       # DOCX parsing

# NLP — Entity & Skill Extraction
spacy>=3.7.0             # Core NLP engine
# After installing spaCy, run:
#   python -m spacy download en_core_web_sm
#   python -m spacy download en_core_web_lg   # optional, for SkillNER

# Skill extraction helpers
# skillner>=1.0.0        # Optional ML-based skill extractor (pip install skillner)

# Semantic Matching
sentence-transformers>=2.7.0   # sentence-transformers with all-MiniLM-L6-v2
torch>=2.0.0                   # Required backend for sentence-transformers
numpy>=1.24.0

# Fallback similarity (if sentence-transformers unavailable)
scikit-learn>=1.3.0

# ── Installation Steps ──────────────────────────────────────────────────────
# 1. pip install -r requirements.txt
# 2. python -m spacy download en_core_web_sm
# 3. Optional: python -m spacy download en_core_web_lg  (for SkillNER)
# 4. Register the blueprint in your Flask app (see INTEGRATION.md)
