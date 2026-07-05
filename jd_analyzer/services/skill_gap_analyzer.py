"""
Skill Gap Analysis Service
Computes matched, missing, and extra skills between JD and resume.
Ranks missing skills by priority (Critical / High / Medium / Low).
"""

import logging
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

# Priority weights by category
PRIORITY_MAP = {
    # Critical — core technical requirements
    "programming_languages": "Critical",
    "backend": "Critical",
    "database": "Critical",
    # High — important technical skills
    "cloud": "High",
    "devops": "High",
    "ai_ml": "High",
    "frontend": "High",
    # Medium — useful but not blocking
    "data_science": "Medium",
    "mobile": "Medium",
    "testing": "Medium",
    "security": "Medium",
    "version_control": "Medium",
    # Low — good to have
    "tools": "Low",
    "operating_systems": "Low",
    "soft_skills": "Low",
}

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]


class SkillGapAnalyzerService:
    """
    Performs set-based skill gap analysis with priority ranking.
    """

    def __init__(self, skill_extractor):
        self._skill_extractor = skill_extractor

    def analyze(
        self,
        jd_skills: Dict[str, List[str]],
        resume_skills: Dict[str, List[str]],
    ) -> Dict:
        """
        Compute gap between JD requirements and resume capabilities.

        Args:
            jd_skills: Categorized skills from the JD.
            resume_skills: Categorized skills from the resume.

        Returns:
            {
              "matched": list[str],
              "missing": list[dict],   # [{skill, category, priority}]
              "extra": list[str],
              "match_rate": float,
              "priority_breakdown": {Critical: [...], High: [...], ...}
            }
        """
        jd_set = set(jd_skills.get("all", []))
        resume_set = set(resume_skills.get("all", []))

        matched = sorted(jd_set & resume_set)
        missing_raw = sorted(jd_set - resume_set)
        extra = sorted(resume_set - jd_set)

        # Build detailed missing list with priority
        missing = self._rank_missing(missing_raw, jd_skills)

        # Priority breakdown
        priority_breakdown: Dict[str, List[str]] = {p: [] for p in PRIORITY_ORDER}
        for item in missing:
            priority_breakdown[item["priority"]].append(item["skill"])

        # Match rate (skills matched / total jd skills)
        match_rate = (len(matched) / len(jd_set) * 100) if jd_set else 0.0

        return {
            "matched": matched,
            "missing": missing,
            "extra": extra,
            "match_rate": round(match_rate, 2),
            "priority_breakdown": priority_breakdown,
            "total_jd_skills": len(jd_set),
            "total_resume_skills": len(resume_set),
            "total_matched": len(matched),
        }

    def _rank_missing(
        self, missing_skills: List[str], jd_skills: Dict[str, List[str]]
    ) -> List[Dict]:
        """
        Assign a priority to each missing skill based on its category in the JD.
        Returns list sorted by priority (Critical first).
        """
        result = []

        # Build inverse map: skill → category from JD skills
        skill_category_map: Dict[str, str] = {}
        from .skill_extractor import SKILL_CATEGORIES
        for cat in SKILL_CATEGORIES:
            for skill in jd_skills.get(cat, []):
                skill_category_map[skill.lower()] = cat

        for skill in missing_skills:
            category = skill_category_map.get(skill.lower(), "tools")
            priority = PRIORITY_MAP.get(category, "Low")
            result.append(
                {
                    "skill": skill,
                    "category": category,
                    "priority": priority,
                    "resources": self._skill_extractor.get_learning_resources(skill),
                }
            )

        # Sort by priority order
        priority_rank = {p: i for i, p in enumerate(PRIORITY_ORDER)}
        result.sort(key=lambda x: priority_rank.get(x["priority"], 99))
        return result
