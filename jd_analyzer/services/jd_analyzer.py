"""
JD Analyzer Orchestrator
Coordinates all sub-services into a single analysis pipeline.

Pipeline:
  1. Parse file → raw text
  2. Normalize text
  3. Extract JD entities
  4. Extract JD skills
  5. Extract resume skills (if resume text provided)
  6. Skill gap analysis
  7. Semantic matching
  8. Scoring
  9. Assemble final report
"""

import logging
import time
from typing import Dict, Any, Optional

from .file_parser import FileParserService
from .entity_extractor import EntityExtractorService
from .skill_extractor import SkillExtractorService, CATEGORY_DISPLAY_NAMES
from .skill_gap_analyzer import SkillGapAnalyzerService
from .semantic_matcher import SemanticMatcherService
from .scoring_engine import ScoringEngineService
from .jd_validator import JDValidatorService
from ..utils.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class JDAnalyzerService:
    """
    Top-level service for the JD Analyzer feature.
    Instantiate once (app-level) and call .analyze() per request.
    """

    def __init__(self):
        logger.info("[JDAnalyzer] Initializing services...")
        self.file_parser = FileParserService()
        self.normalizer = TextNormalizer()
        self.entity_extractor = EntityExtractorService()
        self.skill_extractor = SkillExtractorService()
        self.skill_gap_analyzer = SkillGapAnalyzerService(self.skill_extractor)
        self.semantic_matcher = SemanticMatcherService()
        self.scoring_engine = ScoringEngineService()
        self.jd_validator = JDValidatorService()
        logger.info("[JDAnalyzer] All services ready.")

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def analyze(
        self,
        *,
        jd_file=None,
        jd_filename: str = "",
        jd_text: str = "",
        resume_file=None,
        resume_filename: str = "",
        resume_text: str = "",
    ) -> Dict[str, Any]:
        """
        Run the full JD analysis pipeline.

        Provide EITHER:
          - jd_file + jd_filename  (uploaded file)
          - jd_text                (raw text pasted by user)

        Optionally provide resume content for gap analysis and scoring.

        Returns: Comprehensive analysis report dict.
        """
        start_time = time.time()

        # ----------------------------------------------------------------
        # Step 1 — Parse JD
        # ----------------------------------------------------------------
        if jd_file and jd_filename:
            raw_jd = self.file_parser.parse(jd_file, jd_filename)
        elif jd_text:
            raw_jd = jd_text
        else:
            raise ValueError("Provide either a JD file or JD text.")

        # ----------------------------------------------------------------
        # Step 2 — Normalize
        # ----------------------------------------------------------------
        clean_jd = self.normalizer.normalize(raw_jd, preserve_case=True)
        clean_jd_lower = self.normalizer.normalize(raw_jd, preserve_case=False)

        # ----------------------------------------------------------------
        # Step 2.5 — Validation
        # ----------------------------------------------------------------
        validation_result = self.jd_validator.validate(clean_jd)
        if not validation_result.get("valid_jd"):
            logger.warning(f"[JDAnalyzer] Validation failed: {validation_result.get('message')}")
            return {
                "status": "success",  # Return success to not trigger generic 500 error, but include valid_jd flag
                "valid_jd": False,
                "validation_confidence": validation_result.get("confidence", 0),
                "message": validation_result.get("message")
            }

        # ----------------------------------------------------------------
        # Step 3 — Entity extraction
        # ----------------------------------------------------------------
        try:
            logger.info("[JD] Entity extraction started")
            t0_ent = time.perf_counter()
            logger.info("[JD] Calling entity_extractor.extract()")
            jd_entities = self.entity_extractor.extract(clean_jd)
            logger.info("[JD] entity_extractor.extract() returned")
            logger.info(f"[JD] Entity extraction finished in {time.perf_counter() - t0_ent:.2f} sec")
        except Exception as e:
            logger.error(f"[JD] Error in Entity extraction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        # ----------------------------------------------------------------
        # Step 4 — JD Skill extraction
        # ----------------------------------------------------------------
        try:
            logger.info("[JD] Skill extraction started")
            t0_skill = time.perf_counter()
            logger.info("[JD] Calling skill_extractor.extract()")
            jd_skills = self.skill_extractor.extract(clean_jd_lower)
            logger.info("[JD] skill_extractor.extract() returned")
            logger.info(f"[JD] Skill extraction finished in {time.perf_counter() - t0_skill:.2f} sec")
        except Exception as e:
            logger.error(f"[JD] Error in Skill extraction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        # ----------------------------------------------------------------
        # Step 5 — Resume parsing (optional)
        # ----------------------------------------------------------------
        raw_resume = ""
        resume_entities: Dict[str, Any] = {}
        resume_skills: Dict[str, Any] = {"all": []}

        if resume_file and resume_filename:
            raw_resume = self.file_parser.parse(resume_file, resume_filename)
        elif resume_text:
            raw_resume = resume_text

        if raw_resume:
            clean_resume = self.normalizer.normalize(raw_resume, preserve_case=False)
            resume_entities = self.entity_extractor.extract(raw_resume)
            resume_skills = self.skill_extractor.extract(clean_resume)

        # ----------------------------------------------------------------
        # Step 6 — Skill gap analysis
        # ----------------------------------------------------------------
        try:
            skill_gap = self.skill_gap_analyzer.analyze(jd_skills, resume_skills)
        except Exception as e:
            logger.error(f"[JD] Error in Skill gap analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        # ----------------------------------------------------------------
        # Step 7 — Semantic matching
        # ----------------------------------------------------------------
        try:
            logger.info("[JD] Semantic matching started")
            t0_sem = time.perf_counter()
            semantic_scores = self.semantic_matcher.compute_similarity(
                jd_text=clean_jd_lower,
                resume_text=raw_resume,
                jd_skills=jd_skills.get("all", []),
                resume_skills=resume_skills.get("all", []),
            )
            logger.info(f"[JD] Semantic matching finished in {time.perf_counter() - t0_sem:.2f} sec")
        except Exception as e:
            logger.error(f"[JD] Error in Semantic matching: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        # ----------------------------------------------------------------
        # Step 8 — Scoring
        # ----------------------------------------------------------------
        try:
            logger.info("[JD] About to score")
            t0_score = time.perf_counter()
            scores = self.scoring_engine.score(
                skill_gap=skill_gap,
                jd_entities=jd_entities,
                resume_entities=resume_entities,
                semantic_scores=semantic_scores,
            )
            logger.info(f"[JD] Score complete in {time.perf_counter() - t0_score:.2f} sec")
        except Exception as e:
            logger.error(f"[JD] Error in Scoring: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        # ----------------------------------------------------------------
        # Step 9 — Learning resources for missing skills
        # ----------------------------------------------------------------
        learning_resources = self._build_learning_resources(skill_gap)

        elapsed = round(time.time() - start_time, 2)

        # ----------------------------------------------------------------
        # Assemble final report
        # ----------------------------------------------------------------
        return {
            "status": "success",
            "valid_jd": True,
            "validation_confidence": validation_result.get("confidence", 100),
            "processing_time_sec": elapsed,
            # JD Info
            "jd_entities": jd_entities,
            "jd_skills": {
                "categorized": self._format_categorized(jd_skills),
                "all": jd_skills.get("all", []),
                "total": len(jd_skills.get("all", [])),
            },
            # Resume Info
            "resume_provided": bool(raw_resume),
            "resume_entities": resume_entities,
            "resume_skills": {
                "categorized": self._format_categorized(resume_skills),
                "all": resume_skills.get("all", []),
                "total": len(resume_skills.get("all", [])),
            },
            # Gap Analysis
            "skill_gap": {
                "matched": skill_gap["matched"],
                "missing": skill_gap["missing"],
                "extra": skill_gap["extra"],
                "match_rate": skill_gap["match_rate"],
                "priority_breakdown": skill_gap["priority_breakdown"],
                "stats": {
                    "total_jd_skills": skill_gap["total_jd_skills"],
                    "total_resume_skills": skill_gap["total_resume_skills"],
                    "total_matched": skill_gap["total_matched"],
                },
            },
            # Semantic Scores
            "semantic": semantic_scores,
            # Scores
            "scores": scores,
            # Learning Resources
            "learning_resources": learning_resources,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_categorized(skills_dict: Dict) -> Dict:
        """Add display names to categorized skill dict."""
        result = {}
        for cat, display_name in CATEGORY_DISPLAY_NAMES.items():
            skills_in_cat = skills_dict.get(cat, [])
            if skills_in_cat:
                result[cat] = {
                    "display_name": display_name,
                    "skills": skills_in_cat,
                    "count": len(skills_in_cat),
                }
        return result

    @staticmethod
    def _build_learning_resources(skill_gap: Dict) -> Dict:
        """
        Return learning resources only for missing skills with priority Critical/High.
        """
        resources = {}
        for item in skill_gap.get("missing", []):
            if item["priority"] in ("Critical", "High", "Medium"):
                resources[item["skill"]] = {
                    "priority": item["priority"],
                    "category": item["category"],
                    "resources": item.get("resources", {}),
                }
        return resources
