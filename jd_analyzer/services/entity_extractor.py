"""
Entity Extraction Service
Extracts structured entities from JD text:
  - Job title, company, experience, education, certifications,
    responsibilities, requirements.
Uses spaCy NER + curated regex patterns.
"""

import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# Experience: "3+ years", "2-5 years", "minimum 3 years", etc.
_EXP_PATTERNS = [
    re.compile(
        r"(\d+\s*[\+\-–]\s*\d*)\s+years?\s+(?:of\s+)?(?:experience|exp)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:minimum|at least|min\.?)\s+(\d+)\s+years?\s+(?:of\s+)?(?:experience|exp)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+)\s+to\s+(\d+)\s+years?\s+(?:of\s+)?(?:experience|exp)",
        re.IGNORECASE,
    ),
    re.compile(r"(\d+)\+?\s+years?\s+(?:of\s+)?(?:experience|exp)", re.IGNORECASE),
    re.compile(r"experience\s*(?:of|:)?\s*(\d+\+?\s+years?)", re.IGNORECASE),
]

# Education level keywords
_EDU_DEGREES = [
    r"ph\.?d\.?|doctorate",
    r"master'?s?|m\.?s\.?c?\.?|m\.?eng\.?|mba",
    r"bachelor'?s?|b\.?s\.?c?\.?|b\.?e\.?|b\.?tech\.?|b\.?a\.?",
    r"associate'?s?|a\.?a\.?s?",
    r"diploma|certificate|certification",
]
_EDU_RE = re.compile(
    r"(?:" + "|".join(_EDU_DEGREES) + r")"
    r"(?:\s+(?:degree|in|of)\s+[\w\s,&]+)?",
    re.IGNORECASE,
)

# Certification patterns
_CERT_KEYWORDS = [
    "aws certified", "gcp certified", "azure certified",
    "pmp", "cissp", "ceh", "ccna", "ccnp", "cka", "ckad",
    "google cloud certified", "terraform associate",
    "kubernetes certified", "cpa", "cfa", "six sigma",
    "scrum master", "csm", "safe", "itil", "comptia",
    "oracle certified", "microsoft certified", "red hat",
    "rhce", "lpic", "linux foundation",
]
_CERT_RE = re.compile(
    r"(?:" + "|".join(re.escape(c) for c in _CERT_KEYWORDS) + r")"
    r"[\w\s\-]*",
    re.IGNORECASE,
)

# Section header markers
_SECTION_MARKERS = {
    "responsibilities": [
        r"responsibilities?", r"what you['']ll do", r"key duties",
        r"your role", r"job duties", r"role & responsibilities",
    ],
    "requirements": [
        r"requirements?", r"qualifications?", r"what we['']re looking for",
        r"must have", r"mandatory", r"required skills?",
        r"skills? required", r"minimum qualifications?",
    ],
    "preferred": [
        r"preferred", r"nice to have", r"bonus", r"good to have",
        r"plus", r"additional qualifications?",
    ],
}

_SECTION_RE: Dict[str, re.Pattern] = {
    key: re.compile(
        r"(?:^|\n)(?:" + "|".join(markers) + r")\s*[:\-]?\s*\n",
        re.IGNORECASE | re.MULTILINE,
    )
    for key, markers in _SECTION_MARKERS.items()
}

_TITLE_RE = re.compile(r'(?:job title|position|role|opening|internship title)\s*[:\-]\s*(.+)', re.IGNORECASE)
_COMPANY_RE_DIRECT = re.compile(r'(?:company|organization|employer)\s*[:\-]\s*([A-Za-z0-9&\s]+)', re.IGNORECASE)

SLOGAN_WORDS = [
    'heart of', 'innovation', 'mission', 'vision', 'we are', 'organizing', 
    'world', 'work hard', 'have fun', 'make history', 'engineering intelligence', 
    'building', 'creating', 'empowering', 'revolutionizing'
]


class EntityExtractorService:
    """
    Extracts key entities from a job description using regex + spaCy.
    Strictly filters out marketing slogans to prevent false positives.
    """

    def __init__(self):
        self._nlp = self._load_spacy()

    @staticmethod
    def _load_spacy():
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            logger.info("[EntityExtractor] spaCy model loaded.")
            return nlp
        except (ImportError, OSError) as e:
            logger.warning(f"[EntityExtractor] spaCy unavailable: {e}. Using regex only.")
            return None

    def _is_slogan(self, text: str, max_words=8) -> bool:
        text_lower = text.lower()
        if len(text.split()) > max_words: return True
        if any(p in text for p in ['.', '!', '?']): return True
        if any(w in text_lower for w in SLOGAN_WORDS): return True
        if 'responsibilities' in text_lower or 'you will' in text_lower or 'in this role' in text_lower: return True
        return False

    def extract(self, text: str) -> Dict[str, Any]:
        c_name, c_conf = self._extract_company(text)
        r_name, r_conf = self._extract_job_title(text, c_name)
        
        if r_conf < 0.70:
            r_name = "Not Clearly Mentioned"
            
        entities: Dict[str, Any] = {
            "job_title": r_name,
            "company": c_name,
            "company_confidence": c_conf,
            "role_confidence": r_conf,
            "employment_type": self._extract_employment_type(text),
            "location": self._extract_location(text),
            "work_mode": self._extract_work_mode(text),
            "experience_required": self._extract_experience(text),
            "education_required": self._extract_education(text),
            "certifications": self._extract_certifications(text),
            "responsibilities": self._extract_section(text, "responsibilities"),
            "requirements": self._extract_section(text, "requirements"),
        }

        logger.debug(f"[EntityExtractor] Entities: {entities}")
        return entities

    def _extract_job_title(self, text: str, company_name: str) -> tuple:
        m = _TITLE_RE.search(text)
        if m:
            candidate = m.group(1).splitlines()[0].strip()
            if not self._is_slogan(candidate, max_words=12) and candidate.lower() != company_name.lower():
                return self._clean_entity(candidate), 1.0
                
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for line in lines[:4]:
            if not self._is_slogan(line, max_words=8):
                if company_name and line.lower() == company_name.lower():
                    continue
                if 'about' in line.lower() or 'location:' in line.lower() or 'type:' in line.lower():
                    continue
                return self._clean_entity(line), 0.8
                    
        return 'Not Clearly Mentioned', 0.0

    def _extract_company(self, text: str) -> tuple:
        m = _COMPANY_RE_DIRECT.search(text)
        if m:
            c = m.group(1).splitlines()[0].strip()
            if not self._is_slogan(c, max_words=5):
                return self._clean_entity(c), 1.0
                
        m_about = re.search(r'^About\s+([A-Z][a-zA-Z0-9\s\-&]+?)\s*[:\n]', text, re.IGNORECASE | re.MULTILINE)
        if m_about:
            c = m_about.group(1).strip()
            if not self._is_slogan(c, max_words=5):
                return self._clean_entity(c), 0.9
                
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            c = lines[0]
            if not self._is_slogan(c, max_words=3) and not c.lower().startswith('role'):
                return self._clean_entity(c), 0.8
                
        if self._nlp:
            doc = self._nlp(text[:2000])
            orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            for org in orgs:
                if not self._is_slogan(org, max_words=5):
                    return self._clean_entity(org), 0.6
                    
        return 'Not specified', 0.0

    def _extract_employment_type(self, text: str) -> str:
        text_lower = text.lower()
        if 'internship + ppo' in text_lower or 'pre placement offer' in text_lower or 'ppo' in text_lower:
            return 'Internship + PPO'
        if 'internship' in text_lower or 'intern' in text_lower:
            return 'Internship'
        if 'full time' in text_lower or 'full-time' in text_lower:
            return 'Full Time'
        if 'contract' in text_lower:
            return 'Contract'
        return 'Unknown'

    def _extract_work_mode(self, text: str) -> str:
        text_lower = text.lower()
        if 'remote' in text_lower: return 'Remote'
        if 'hybrid' in text_lower: return 'Hybrid'
        if 'onsite' in text_lower or 'on-site' in text_lower: return 'Onsite'
        return 'Unknown'

    def _extract_location(self, text: str) -> str:
        m = re.search(r'(?:location|based in)\s*[:\-]\s*([A-Za-z0-9,\s]+)', text, re.IGNORECASE)
        if m:
            return self._clean_entity(m.group(1).splitlines()[0].strip())
        return 'Unknown'

    @staticmethod
    def _extract_experience(text: str) -> str:
        for pattern in _EXP_PATTERNS:
            m = pattern.search(text)
            if m:
                return m.group(0).strip()
        return "Not specified"

    @staticmethod
    def _extract_education(text: str) -> List[str]:
        found = []
        for m in _EDU_RE.finditer(text):
            candidate = m.group(0).strip()
            if candidate and candidate not in found:
                found.append(candidate)
        return found if found else ["Not specified"]

    @staticmethod
    def _extract_certifications(text: str) -> List[str]:
        found = []
        for m in _CERT_RE.finditer(text):
            candidate = m.group(0).strip()
            if candidate and candidate not in found:
                found.append(candidate)
        return found

    @staticmethod
    def _extract_section(text: str, section_key: str) -> List[str]:
        """Extract bullet items from a named section of the JD."""
        pattern = _SECTION_RE.get(section_key)
        if not pattern:
            return []

        match = pattern.search(text)
        if not match:
            return []

        # Grab text after the section header until next blank+header
        start = match.end()
        remaining = text[start:]

        # Find the next section header
        end_markers = [
            re.search(p, remaining, re.IGNORECASE | re.MULTILINE)
            for markers in _SECTION_MARKERS.values()
            for p in [r"(?:^|\n)(?:" + "|".join(markers) + r")\s*[:\-]?\s*\n"]
        ]
        end_positions = [m.start() for m in end_markers if m]
        section_text = remaining[: min(end_positions)] if end_positions else remaining[:2000]

        # Split into lines and clean
        items = []
        for line in section_text.splitlines():
            line = re.sub(r"^[\s•·▪▸►◦‣⁃\-–—*\d\.]+", "", line).strip()
            if len(line) > 10:
                items.append(line)

        return items[:20]

    @staticmethod
    def _clean_entity(text: str) -> str:
        """Strip trailing punctuation and whitespace from an entity."""
        return re.sub(r"[,;:\.\-]+$", "", text).strip()
