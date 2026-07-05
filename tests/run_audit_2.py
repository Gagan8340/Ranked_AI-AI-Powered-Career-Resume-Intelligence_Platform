from utils.gemini_helper import analyze_jd_match

def run_ats_audit_part2():
    print("\\n=== AUDIT 2: ATS CHECKER (Part 2) ===")
    
    genericDummyJd = "This is a generic baseline professional job description designed to evaluate a resume's Applicant Tracking System (ATS) compatibility. It requires standard professional formatting, clear experience bullet points with measurable achievements, appropriate industry keywords, educational background, and a comprehensive skills section. We are looking for candidates who demonstrate strong communication, leadership, problem-solving abilities, and relevant technical competencies tailored to standard corporate environments."
    
    resumes = [
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
    run_ats_audit_part2()
