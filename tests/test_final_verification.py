import json
import logging

from jd_analyzer.services.jd_analyzer import JDAnalyzerService

logging.basicConfig(level=logging.ERROR)

analyzer = JDAnalyzerService()

resume_text = """
I am a software engineer with 2 years of experience.
I have worked extensively with Python, Django, HTML, and CSS.
I also have experience with Pandas and Data Analysis.
My projects involve building web applications and writing clean code.
"""

jds = {
    "Python Developer": """
        We are seeking a Python Developer with 3+ years of experience.
        Must have strong skills in Python, Django, SQL, and AWS.
        Experience with Docker and Kubernetes is a plus.
        Must know how to build REST APIs and write test cases.
    """,
    "Data Scientist": """
        Looking for a Data Scientist to join our team.
        You should have experience with Python, Machine Learning, Data Science, and NLP.
        Skills required: Pandas, NumPy, Scikit-Learn, PyTorch, SQL.
        Must have good communication skills and ability to solve problems.
    """,
    "Full Stack Developer": """
        We need a Full Stack Developer.
        Required Skills: JavaScript, React, Node.js, Express, MongoDB.
        Experience with HTML, CSS, and Git.
        Understanding of System Design and Agile methodologies.
    """
}

for role, jd_text in jds.items():
    print(f"\n=================================================")
    print(f"VERIFYING: {role}")
    print(f"=================================================")
    
    raw_analysis = analyzer.analyze(jd_text=jd_text, resume_text=resume_text)
    
    scores = raw_analysis.get('scores', {})
    skill_gap = raw_analysis.get('skill_gap', {})
    jd_skills = raw_analysis.get('jd_skills', {}).get('all', [])
    
    missing_skills = [obj.get('skill') for obj in skill_gap.get('missing', [])]
    
    # Simulating intelligence_routes.py roadmap mapping
    priority_skills = missing_skills[:5] if missing_skills else jd_skills[:5]
    project_gaps = missing_skills if missing_skills else jd_skills[:3]
    interview_topics = priority_skills
    
    phases = []
    target_skills = priority_skills if priority_skills else jd_skills[:3]
    if target_skills:
        for idx, skill in enumerate(target_skills, start=1):
            phases.append(f"Phase {idx}: Master {skill}")
    else:
        phases.append("Interview Preparation")
        
    print(f"* Extracted JD Skills: {', '.join(jd_skills)}")
    print(f"* Missing Skills: {', '.join(missing_skills) if missing_skills else 'None!'}")
    print(f"* Match Score: {scores.get('overall_score')}%")
    print(f"* Roadmap Phases: {', '.join(phases)}")
    print(f"* Project Recommendations based on: {', '.join(project_gaps)}")
    print(f"* Interview Questions based on: {', '.join(interview_topics)}")
