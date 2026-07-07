"""
Skill Extraction Service
Combines three extraction strategies:
  1. Custom Skill Database (fast dictionary lookup)
  2. spaCy PhraseMatcher (tokenized matching with NLP)
  3. SkillNER (ML-based skill recognition, optional)

Categorizes skills into 15 technology domains.
"""

import json
import logging
import os
import re
from typing import Dict, List, Set, Optional, Tuple

logger = logging.getLogger(__name__)

# Path to the skill database
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "skill_database.json")

# Skill categories (ordered for display)
SKILL_CATEGORIES = [
    "programming_languages",
    "frontend",
    "backend",
    "database",
    "cloud",
    "devops",
    "ai_ml",
    "data_science",
    "mobile",
    "testing",
    "security",
    "soft_skills",
    "tools",
    "operating_systems",
    "version_control",
]

CATEGORY_DISPLAY_NAMES = {
    "programming_languages": "Programming Languages",
    "frontend": "Frontend",
    "backend": "Backend",
    "database": "Database",
    "cloud": "Cloud",
    "devops": "DevOps",
    "ai_ml": "AI / ML",
    "data_science": "Data Science",
    "mobile": "Mobile",
    "testing": "Testing",
    "security": "Security",
    "soft_skills": "Soft Skills",
    "tools": "Tools",
    "operating_systems": "Operating Systems",
    "version_control": "Version Control",
}


class SkillExtractorService:
    """
    Multi-strategy skill extractor with category classification.
    """

    def __init__(self):
        self._db = self._load_skill_db()
        self._flat_skills, self._skill_to_category = self._build_indexes()
        self._nlp = self._load_spacy()
        self._matcher = self._build_matcher() if self._nlp else None
        logger.info(
            f"[SkillExtractor] Loaded {len(self._flat_skills)} skills across "
            f"{len(SKILL_CATEGORIES)} categories."
        )

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_skill_db() -> Dict:
        try:
            with open(_DB_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[SkillExtractor] Failed to load skill DB: {e}")
            return {}

    def _build_indexes(self) -> Tuple[Set[str], Dict[str, str]]:
        """Build a flat set of skills and a skill→category mapping."""
        flat: Set[str] = set()
        mapping: Dict[str, str] = {}

        for category in SKILL_CATEGORIES:
            cat_data = self._db.get(category, {})
            skills = cat_data.get("skills", [])
            aliases = cat_data.get("aliases", {})

            for skill in skills:
                normalized = skill.lower().strip()
                flat.add(normalized)
                mapping[normalized] = category

            for alias, canonical in aliases.items():
                normalized_alias = alias.lower().strip()
                normalized_canon = canonical.lower().strip()
                flat.add(normalized_alias)
                mapping[normalized_alias] = category
                # Ensure canonical is also indexed
                flat.add(normalized_canon)
                if normalized_canon not in mapping:
                    mapping[normalized_canon] = category

        return flat, mapping

    @staticmethod
    def _load_spacy():
        try:
            from .model_cache import get_spacy_model
            return get_spacy_model()
        except Exception as e:
            logger.warning(f"[SkillExtractor] spaCy unavailable: {e}")
            return None

    def _build_matcher(self):
        """Build a spaCy PhraseMatcher with all known skills."""
        try:
            from spacy.matcher import PhraseMatcher
            matcher = PhraseMatcher(self._nlp.vocab, attr="LOWER")
            patterns = list(self._nlp.pipe(list(self._flat_skills)))
            matcher.add("SKILLS", patterns)
            return matcher
        except Exception as e:
            logger.warning(f"[SkillExtractor] PhraseMatcher build failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extract and categorize skills from text.

        Returns:
            {
              "all": ["python", "docker", ...],
              "programming_languages": [...],
              "frontend": [...],
              ...  (one key per category)
            }
        """
        found: Set[str] = set()

        # Strategy 1: Fast dictionary lookup (regex word-boundary matching)
        found.update(self._db_lookup(text))

        # Strategy 2: spaCy PhraseMatcher (more robust tokenization)
        if self._nlp and self._matcher:
            found.update(self._spacy_match(text))

        # Strategy 3: SkillNER (ML-based, optional)
        found.update(self._skillner_extract(text))

        # Categorize results
        return self._categorize(found)

    def get_learning_resources(self, skill: str) -> Dict:
        """Return learning resources for a given skill."""
        resources = self._db.get("learning_resources", {})
        skill_lower = skill.lower()
        # Try exact match first, then partial
        if skill_lower in resources:
            return resources[skill_lower]
        for key in resources:
            if key in skill_lower or skill_lower in key:
                return resources[key]
        return resources.get("default", {})

    # ------------------------------------------------------------------
    # Extraction strategies
    # ------------------------------------------------------------------

    def _db_lookup(self, text: str) -> Set[str]:
        """Dictionary-based lookup using word-boundary regex."""
        found: Set[str] = set()
        text_lower = text.lower()

        for skill in self._flat_skills:
            # Use word boundaries; also handle dots/plus in skill names
            pattern = r"(?<![a-z0-9\.\+])" + re.escape(skill) + r"(?![a-z0-9\.\+])"
            if re.search(pattern, text_lower):
                found.add(self._canonicalize(skill))

        return found

    def _spacy_match(self, text: str) -> Set[str]:
        """spaCy PhraseMatcher — handles multi-word skills reliably."""
        found: Set[str] = set()
        try:
            doc = self._nlp(text[:50000])  # cap for performance
            matches = self._matcher(doc)
            for _, start, end in matches:
                span_text = doc[start:end].text.lower()
                found.add(self._canonicalize(span_text))
        except Exception as e:
            logger.warning(f"[SkillExtractor] spaCy match error: {e}")
        return found

    def _skillner_extract(self, text: str) -> Set[str]:
        """Optional SkillNER extraction (graceful fallback if not installed)."""
        import os
        use_skillner = os.getenv("USE_SKILLNER", "false").lower() in ("true", "1", "yes")
        
        if not use_skillner:
            logger.info("[JD] SkillNER disabled; using deterministic extraction only")
            return set()
            
        found: Set[str] = set()
        try:
            import spacy
            from skillner import SkillExtractor as SNExtractor

            # SkillNER needs a plain spacy model
            nlp = spacy.load("en_core_web_lg")
            extractor = SNExtractor(nlp)
            doc = nlp(text[:10000])
            doc = extractor(doc)
            for sent in doc.sents:
                for skill in sent._.skills:
                    skill_text = skill["skill"].lower().strip()
                    if skill_text:
                        found.add(self._canonicalize(skill_text))
        except ImportError:
            pass  # SkillNER is optional
        except Exception as e:
            logger.debug(f"[SkillExtractor] SkillNER error: {e}")
        return found

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _canonicalize(self, skill: str) -> str:
        """Resolve alias to canonical skill name."""
        skill_lower = skill.lower().strip()
        for category in SKILL_CATEGORIES:
            aliases = self._db.get(category, {}).get("aliases", {})
            if skill_lower in aliases:
                return aliases[skill_lower].lower()
        return skill_lower

    def _categorize(self, skills: Set[str]) -> Dict[str, List[str]]:
        """Group skills by category and return sorted lists."""
        result: Dict[str, List[str]] = {cat: [] for cat in SKILL_CATEGORIES}
        result["all"] = []

        for skill in skills:
            skill_lower = skill.lower()
            category = self._skill_to_category.get(skill_lower, None)

            if category and category in result:
                if skill_lower not in result[category]:
                    result[category].append(skill_lower)
                if skill_lower not in result["all"]:
                    result["all"].append(skill_lower)
            elif skill_lower:
                # Unknown category — append to tools as catch-all
                if skill_lower not in result.get("tools", []):
                    result.setdefault("tools", []).append(skill_lower)
                if skill_lower not in result["all"]:
                    result["all"].append(skill_lower)

        # Sort each category list
        for key in result:
            result[key] = sorted(result[key])

        return result
