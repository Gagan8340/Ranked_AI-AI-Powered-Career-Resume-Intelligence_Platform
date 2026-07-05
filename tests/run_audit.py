import json
from app import create_app
from config import get_db_connection
from utils.gemini_helper import analyze_jd_match

def run_jd_audit():
    print("=== AUDIT 1: JD ANALYZER ===")
    jds = [
        "Software Engineer with 3 years of Python and Django. Must have Docker experience.",
        "Frontend Developer with 2 years React and TailwindCSS experience. Familiarity with Node.js.",
        "Data Scientist. Needs Python, Pandas, Scikit-learn, and 5 years experience.",
        "Product Manager. Agile, Scrum, leadership, 4 years experience.",
        "DevOps Engineer. Kubernetes, AWS, Terraform, CI/CD pipelines."
    ]
    
    # We use User 11's resume text (Resume ID 17 is a B.Tech student with Python/Flask)
    resume_text = "B.Tech Computer Science student graduating 2027. Experience in Python, Flask, C++, SQL. Projects include a web app and a machine learning model."
    
    results = []
    for i, jd in enumerate(jds):
        try:
            res = analyze_jd_match(resume_text, jd)
            print(f"\\nJD {i+1}: {jd[:30]}...")
            print(f"Title: {res.get('job_title')}")
            print(f"Score: {res.get('ats_score')}")
            print(f"Missing: {res.get('missing_keywords', [])}")
            print(f"Recommendations: {res.get('recommendations', [])[0] if res.get('recommendations') else 'None'}")
            results.append(res)
        except Exception as e:
            print(f"JD {i+1} Failed: {e}")
            
    return results

def run_ats_audit():
    print("\\n=== AUDIT 2: ATS CHECKER ===")
    
    genericDummyJd = "This is a generic baseline professional job description designed to evaluate a resume's Applicant Tracking System (ATS) compatibility. It requires standard professional formatting, clear experience bullet points with measurable achievements, appropriate industry keywords, educational background, and a comprehensive skills section. We are looking for candidates who demonstrate strong communication, leadership, problem-solving abilities, and relevant technical competencies tailored to standard corporate environments."
    
    resumes = [
        {"type": "Empty Resume", "text": ""},
        {"type": "Basic Resume", "text": "John Doe. I am looking for a job. I know computers."},
        {"type": "Strong Resume", "text": "Senior Software Engineer with 8 years of experience building scalable microservices. Proficient in Python, Java, AWS, Kubernetes, and Docker. Led a team of 5 engineers to deliver a high-traffic e-commerce platform. Strong communication and leadership skills. Excellent problem-solving abilities in corporate environments. B.S. in Computer Science."}
    ]
    
    for r in resumes:
        try:
            res = analyze_jd_match(r['text'], genericDummyJd)
            print(f"\\nType: {r['type']}")
            print(f"Score: {res.get('ats_score')}")
            print(f"Weak Areas: {res.get('weak_areas', [])}")
        except Exception as e:
            print(f"{r['type']} Failed: {e}")

if __name__ == "__main__":
    run_jd_audit()
    run_ats_audit()
