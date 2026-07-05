import json
from jd_analyzer.services.jd_analyzer import JDAnalyzerService
from jd_analyzer.services.recommendation_engine import RecommendationEngine

jds = [
    {
        "name": "Kalvium Teaching Ninja",
        "text": "About Kalvium:\nKalvium is an Education Company.\nKalvium Teaching Ninjas (DSA + Tech Skilling)\nRequirements:\n- DSA\n- Problem Solving\n- Mentoring and Teaching\n- Competitive Coding"
    },
    {
        "name": "Python Developer",
        "text": "Position: Python Backend Developer\nCompany: TechCorp\nRequirements:\n- Python\n- SQL\n- System Design\n- Django/Flask"
    },
    {
        "name": "Full Stack Developer",
        "text": "About StartupX: We build web apps.\nTitle: Full Stack Developer\nRequirements:\n- React\n- Node.js\n- SQL\n- AWS"
    },
    {
        "name": "Data Scientist",
        "text": "Position: Data Scientist\nCompany: DataCo\nRequirements:\n- Machine Learning\n- Python\n- Statistics\n- NLP\n- SQL"
    }
]

analyzer = JDAnalyzerService()
engine = RecommendationEngine()

results = {}

for jd in jds:
    print(f"Analyzing {jd['name']}...")
    # Empty resume to simulate 0% match and force missing skills
    analysis = analyzer.analyze(jd_text=jd['text'], resume_text="Resume:\n- HTML\n- CSS")
    
    entities = analysis.get('jd_entities', {})
    company = entities.get('company', 'Unknown')
    role = entities.get('job_title', 'Unknown')
    
    missing_skills = [obj.get('skill') for obj in analysis.get('skill_gap', {}).get('missing', [])]
    jd_skills = analysis.get('jd_skills', {}).get('all', [])
    
    projects = engine.generate_project_recommendations(role, missing_skills, jd_skills)
    interviews = engine.generate_interview_prep(missing_skills, jd_skills)
    experience = engine.generate_experience_improvements(role, missing_skills)
    roadmap = engine.generate_roadmap_phases(role, company, missing_skills, jd_skills)
    
    results[jd['name']] = {
        "Company Extracted": company,
        "Role Extracted": role,
        "Missing Skills": missing_skills,
        "Top Project": projects[0]['title'] if projects else None,
        "Top Interview Category": interviews[0]['category'] if interviews else None,
        "Experience Recommendation": experience['recommendations'][0] if experience.get('recommendations') else None,
        "Top Roadmap Phase": roadmap[0]['phase'] if roadmap else None,
        "Roadmap Duration": roadmap[0]['duration'] if roadmap else None
    }

with open("data/validation_report.json", "w") as f:
    json.dump(results, f, indent=4)

print("Validation complete. Report saved to data/validation_report.json")
