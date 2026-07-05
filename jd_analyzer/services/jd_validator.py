import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class JDValidatorService:
    """
    Validates whether the provided text is a legitimate Job Description.
    Applies anti-gibberish checks, length checks, and signal counting
    to prevent processing of random or incomplete text.
    """

    def __init__(self):
        self.job_title_indicators = [
            "engineer", "developer", "analyst", "scientist", "manager",
            "intern", "internship", "associate", "architect", "consultant", "lead"
        ]
        
        self.req_indicators = [
            "requirements", "qualifications", "skills", "experience",
            "responsibilities", "what you'll do", "job description", "preferred qualifications"
        ]
        
        self.emp_indicators = [
            "location", "salary", "stipend", "ppo", "internship", "full time", "contract"
        ]

    def _compute_gibberish_ratio(self, text: str) -> float:
        """
        Calculates the ratio of gibberish words to total words.
        A word is considered gibberish if it's too long without vowels,
        or has repeated character patterns (e.g., 'asdffgh', 'fbfbfb').
        """
        words = text.split()
        if not words:
            return 0.0
            
        gibberish_count = 0
        for word in words:
            word = word.lower()
            word = re.sub(r'[^a-z]', '', word)
            if not word:
                continue
                
            # Check for excessive length without vowels
            if len(word) > 7 and not any(v in word for v in 'aeiouy'):
                gibberish_count += 1
                continue
                
            # Check for repeated patterns like fbfbfb
            if re.match(r'^([a-z]{1,2})\1{2,}$', word):
                gibberish_count += 1
                continue
                
            # Check for common keyboard smashes
            if any(smash in word for smash in ['asdf', 'qwer', 'zxcv', 'hjkl']):
                gibberish_count += 1
                continue

        return (gibberish_count / len(words)) * 100

    def validate(self, text: str) -> Dict[str, Any]:
        """
        Validates the JD text and returns confidence and status.
        """
        clean_text = text.strip()
        text_lower = clean_text.lower()
        words = clean_text.split()
        
        # 1. Minimum Content Quality
        if len(clean_text) < 100 or len(words) < 20:
            logger.warning("[JDValidator] Failed minimum length check.")
            return {
                "valid_jd": False,
                "confidence": 0,
                "message": "This does not appear to be a valid Job Description. Please paste the complete job description from a company hiring page, LinkedIn posting, internship posting, or career portal."
            }
            
        # 2. Anti-Gibberish Detection
        gibberish_ratio = self._compute_gibberish_ratio(clean_text)
        if gibberish_ratio > 40:
            logger.warning(f"[JDValidator] Failed gibberish check. Ratio: {gibberish_ratio}%")
            return {
                "valid_jd": False,
                "confidence": 10,
                "message": "This does not appear to be a valid Job Description. Please paste the complete job description from a company hiring page, LinkedIn posting, internship posting, or career portal."
            }
            
        # 3. Job Description Signals
        score = 0
        
        # Base points for length (up to 30 points)
        score += min(30, int((len(words) / 300) * 30))
        
        # Check Title indicators (up to 20 points)
        title_matches = sum(1 for ind in self.job_title_indicators if ind in text_lower)
        score += min(20, title_matches * 10)
        
        # Check Requirement indicators (up to 30 points)
        req_matches = sum(1 for ind in self.req_indicators if ind in text_lower)
        score += min(30, req_matches * 10)
        
        # Check Employment indicators (up to 20 points)
        emp_matches = sum(1 for ind in self.emp_indicators if ind in text_lower)
        score += min(20, emp_matches * 10)
        
        confidence = min(100, score)
        
        logger.info(f"[JDValidator] JD Confidence Score: {confidence}")
        
        # 4. Hard Block
        if confidence < 40:
            return {
                "valid_jd": False,
                "confidence": confidence,
                "message": "This does not appear to be a valid Job Description. Please paste the complete job description from a company hiring page, LinkedIn posting, internship posting, or career portal."
            }
            
        return {
            "valid_jd": True,
            "confidence": confidence,
            "message": "Valid Job Description."
        }
