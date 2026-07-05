"""
Text Normalizer Utility
Cleans and normalizes raw JD / resume text before NLP processing.
"""

import re
import unicodedata
import logging
from typing import List

logger = logging.getLogger(__name__)


class TextNormalizer:
    """
    Provides text cleaning operations:
    - Unicode normalization
    - Whitespace / newline collapsing
    - Special-character removal
    - Lowercase conversion
    - Duplicate line removal
    """

    # Bullets and decorators to strip
    _BULLET_RE = re.compile(r"^[\s•·▪▸►◦‣⁃\-–—*]+", re.MULTILINE)
    # Multiple spaces / tabs
    _SPACES_RE = re.compile(r"[ \t]+")
    # Three+ newlines → two
    _NEWLINES_RE = re.compile(r"\n{3,}")
    # Non-printable chars (keep \n \t)
    _CONTROL_RE = re.compile(r"[^\S\n\t]")
    # Email / URL placeholders (optional: keep for context)
    _URL_RE = re.compile(r"https?://\S+|www\.\S+")
    _EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", re.IGNORECASE)

    def normalize(self, text: str, *, preserve_case: bool = False) -> str:
        """
        Full normalization pipeline.

        Args:
            text: Raw input text.
            preserve_case: If True, skip lowercasing.

        Returns:
            Cleaned, normalized text.
        """
        if not text:
            return ""

        # 1. Unicode NFKC (normalize ligatures, composed chars, etc.)
        text = unicodedata.normalize("NFKC", text)

        # 2. Strip URLs and emails (replace with placeholder)
        text = self._URL_RE.sub(" ", text)
        text = self._EMAIL_RE.sub(" ", text)

        # 3. Remove bullet decorators at line start
        text = self._BULLET_RE.sub("", text)

        # 4. Collapse multiple spaces/tabs
        text = self._SPACES_RE.sub(" ", text)

        # 5. Collapse excessive newlines
        text = self._NEWLINES_RE.sub("\n\n", text)

        # 6. Strip trailing/leading whitespace per line
        lines = [line.strip() for line in text.splitlines()]

        # 7. Remove duplicate lines while preserving order
        seen: set = set()
        deduped: List[str] = []
        for line in lines:
            key = line.lower().strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(line)

        text = "\n".join(deduped)

        # 8. Lowercase (optional)
        if not preserve_case:
            text = text.lower()

        # 9. Final strip
        return text.strip()

    def tokenize(self, text: str) -> List[str]:
        """
        Simple word tokenizer (splits on whitespace and punctuation,
        filters short tokens).
        """
        tokens = re.split(r"[\s,;|/\\()\[\]{}<>\"'`]+", text.lower())
        return [t for t in tokens if len(t) > 1]
