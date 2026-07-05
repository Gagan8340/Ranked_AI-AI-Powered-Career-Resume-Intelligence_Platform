import json
import logging
logging.basicConfig(level=logging.ERROR)

from jd_analyzer.services.jd_analyzer import JDAnalyzerService

jd_text = "We are looking for a Senior Software Engineer with strong Python, AWS, Docker, and Kubernetes skills. 5+ years experience required."
resume_text = "I am a software engineer with 5 years of experience in Python and Kubernetes."

print("Initializing JDAnalyzerService...")
analyzer = JDAnalyzerService()
print("Analyzing...")

raw_analysis = analyzer.analyze(jd_text=jd_text, resume_text=resume_text)

print("\n=== RAW BACKEND SCHEMA ===")
print(json.dumps({
    "jd_skills": raw_analysis.get("jd_skills"),
    "skill_gap": raw_analysis.get("skill_gap"),
    "scores": raw_analysis.get("scores"),
    "learning_resources": raw_analysis.get("learning_resources")
}, indent=2))

scores = raw_analysis.get('scores', {})
skill_gap = raw_analysis.get('skill_gap', {})
jd_skills = raw_analysis.get('jd_skills', {})
jd_entities = raw_analysis.get('jd_entities', {})

ats_score = int(scores.get('overall_score', 0))
missing_skills_list = [obj.get('skill') for obj in skill_gap.get('missing', [])]
jd_required_skills = jd_skills.get('all', [])

frontend_mapped = {
    "ats_score": ats_score,
    "missing_skills": missing_skills_list,
    "jd_required_skills": jd_required_skills,
    "experience_improvements": [f"Gain experience in {s}" for s in missing_skills_list],
    "missing_keywords": missing_skills_list,
    "interview_topics": missing_skills_list[:3] if missing_skills_list else [],
    "job_title": jd_entities.get("job_titles", ["Unknown Role"])[0] if jd_entities.get("job_titles") else "Unknown Role",
    "project_gaps": missing_skills_list,
    "summary_improvements": ["Highlight these skills in your summary: " + ", ".join(missing_skills_list)] if missing_skills_list else ["Summary looks well aligned."]
}

print("\n=== FRONTEND MAPPED SCHEMA (from jd_routes.py) ===")
print(json.dumps(frontend_mapped, indent=2))


