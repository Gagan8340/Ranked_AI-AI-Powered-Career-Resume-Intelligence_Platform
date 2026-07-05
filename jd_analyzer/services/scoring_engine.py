"""
Scoring Engine Service
Computes weighted overall match score from:
  - Skill Score (50%)
  - Experience Score (20%)
  - Education Score (10%)
  - Semantic Similarity Score (20%)
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Scoring weights
WEIGHTS = {
    "skill": 0.50,
    "experience": 0.20,
    "education": 0.10,
    "semantic": 0.20,
}

# Education level hierarchy (higher index = higher level)
EDUCATION_LEVELS = [
    ["high school", "secondary", "diploma"],
    ["associate", "a.a", "a.s"],
    ["bachelor", "b.sc", "b.e", "b.tech", "b.a", "undergraduate"],
    ["master", "m.sc", "m.s", "m.e", "mba", "m.tech", "postgraduate"],
    ["phd", "ph.d", "doctorate", "doctoral"],
]


class ScoringEngineService:
    """
    Produces a weighted overall match percentage with per-component breakdown.
    """

    def score(
        self,
        skill_gap: Dict,
        jd_entities: Dict,
        resume_entities: Dict,
        semantic_scores: Dict,
    ) -> Dict[str, Any]:
        """
        Compute all scores and return a comprehensive report.

        Args:
            skill_gap: Output from SkillGapAnalyzerService.analyze()
            jd_entities: Entities extracted from JD
            resume_entities: Entities extracted from resume (may be partial)
            semantic_scores: Output from SemanticMatcherService.compute_similarity()

        Returns:
            {
              "skill_score": float,
              "experience_score": float,
              "education_score": float,
              "semantic_score": float,
              "overall_score": float,
              "grade": str,
              "verdict": str,
              "breakdown": { ... }
            }
        """
        skill_score = self._skill_score(skill_gap)
        experience_score = self._experience_score(jd_entities, resume_entities)
        education_score = self._education_score(jd_entities, resume_entities)
        semantic_score = semantic_scores.get("overall_semantic_score", 0.0)

        overall = (
            skill_score * WEIGHTS["skill"]
            + experience_score * WEIGHTS["experience"]
            + education_score * WEIGHTS["education"]
            + semantic_score * WEIGHTS["semantic"]
        )
        overall = round(min(overall, 100.0), 2)

        grade = self._grade(overall)
        verdict = self._verdict(overall)

        return {
            "skill_score": round(skill_score, 2),
            "experience_score": round(experience_score, 2),
            "education_score": round(education_score, 2),
            "semantic_score": round(semantic_score, 2),
            "overall_score": overall,
            "grade": grade,
            "verdict": verdict,
            "weights": WEIGHTS,
            "breakdown": {
                "skill_contribution": round(skill_score * WEIGHTS["skill"], 2),
                "experience_contribution": round(experience_score * WEIGHTS["experience"], 2),
                "education_contribution": round(education_score * WEIGHTS["education"], 2),
                "semantic_contribution": round(semantic_score * WEIGHTS["semantic"], 2),
            },
        }

    # ------------------------------------------------------------------
    # Component scorers
    # ------------------------------------------------------------------

    @staticmethod
    def _skill_score(skill_gap: Dict) -> float:
        """matched_skills / total_jd_skills × 100."""
        total = skill_gap.get("total_jd_skills", 0)
        matched = skill_gap.get("total_matched", 0)
        if total == 0:
            return 0.0
        return (matched / total) * 100

    def _experience_score(self, jd_entities: Dict, resume_entities: Dict) -> float:
        """
        Compare required experience vs resume experience.
        Heuristic: extract years from both, compute ratio (capped at 100).
        """
        jd_years = self._extract_years(jd_entities.get("experience_required", ""))
        resume_years = self._extract_years(resume_entities.get("experience_required", ""))

        if jd_years is None:
            return 75.0  # No requirement stated — neutral score

        if resume_years is None:
            return 50.0  # Can't determine resume experience

        if resume_years >= jd_years:
            return 100.0

        # Partial credit: proportional
        return round((resume_years / jd_years) * 100, 2)

    def _education_score(self, jd_entities: Dict, resume_entities: Dict) -> float:
        """
        Compare required education level vs resume education level.
        """
        jd_edu = jd_entities.get("education_required", [])
        resume_edu = resume_entities.get("education_required", [])

        jd_level = self._edu_level(jd_edu)
        resume_level = self._edu_level(resume_edu)

        if jd_level < 0:
            return 80.0  # No specific requirement

        if resume_level < 0:
            return 40.0  # Unknown resume education

        if resume_level >= jd_level:
            return 100.0

        # Partial: each level gap costs 20 points
        gap = jd_level - resume_level
        return max(0.0, 100.0 - gap * 20)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_years(text: str) -> Optional[float]:
        """Extract the minimum years figure from an experience string."""
        if not text or text == "Not specified":
            return None
        # Grab first integer in the string
        m = re.search(r"(\d+(?:\.\d+)?)", text)
        if m:
            return float(m.group(1))
        return None

    @staticmethod
    def _edu_level(edu_list: List[str]) -> int:
        """
        Map education list to a numeric level index.
        Returns -1 if undetermined.
        """
        combined = " ".join(edu_list).lower()
        for level_idx, keywords in reversed(list(enumerate(EDUCATION_LEVELS))):
            if any(kw in combined for kw in keywords):
                return level_idx
        return -1

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"

    @staticmethod
    def _verdict(score: float) -> str:
        if score >= 80:
            return "Excellent Match — Strongly consider applying."
        elif score >= 65:
            return "Good Match — You meet most requirements."
        elif score >= 50:
            return "Fair Match — Some gaps to address before applying."
        elif score >= 35:
            return "Weak Match — Significant skill development needed."
        else:
            return "Poor Match — This role requires substantial upskilling."
