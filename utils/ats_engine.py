import re
import hashlib
from collections import Counter

def generate_resume_hash(resume_text):
    return hashlib.sha256(resume_text.encode('utf-8')).hexdigest()

def extract_sections(text):
    text_lower = text.lower()
    sections = {}
    
    headings = {
        "summary": [r"\bsummary\b", r"\bobjective\b", r"\bprofile\b", r"\bprofessional summary\b"],
        "education": [r"\beducation\b", r"\bacademics\b", r"\bacademic background\b"],
        "experience": [r"\bexperience\b", r"\bemployment\b", r"\bwork history\b", r"\bprofessional experience\b"],
        "projects": [r"\bprojects\b", r"\bacademic projects\b", r"\bpersonal projects\b"],
        "skills": [r"\bskills\b", r"\btechnologies\b", r"\btechnical skills\b"],
        "certifications": [r"\bcertifications\b", r"\blicenses\b"],
        "achievements": [r"\bachievements\b", r"\bawards\b"]
    }
    
    lines = text.split('\n')
    current_section = None
    
    for line in lines:
        cleaned_line = line.strip().lower()
        found_heading = False
        for sec, patterns in headings.items():
            for p in patterns:
                if re.match(f"^{p}$", cleaned_line.strip(':')):
                    current_section = sec
                    sections[sec] = sections.get(sec, "") + "\n"
                    found_heading = True
                    break
            if found_heading: break
            
        if not found_heading and current_section:
            sections[current_section] += line + "\n"
            
    return sections

def calculate_formatting_score(text):
    score = 0
    reasons = []
    improvements = []
    
    # Contact info (10 each, max 30)
    has_email = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text))
    has_phone = bool(re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text))
    has_link = bool(re.search(r"(linkedin\.com|github\.com)", text.lower()))
    
    if has_email: score += 10
    else: improvements.append("Add a professional email address.")
    
    if has_phone: score += 10
    else: improvements.append("Add a contact phone number.")
    
    if has_link: score += 10
    else: improvements.append("Include links to your LinkedIn profile or GitHub repository.")
    
    # Section organization (max 40)
    lines = text.split('\n')
    headings = [l.strip() for l in lines if l.strip().isupper() and len(l.strip()) > 3 and len(l.split()) <= 3]
    if len(headings) >= 4:
        score += 40
    elif len(headings) > 0:
        score += len(headings) * 10
        improvements.append(f"Only {len(headings)} clear section headings found. Use consistent capitalization for headings (e.g., EXPERIENCE, EDUCATION).")
    else:
        improvements.append("No clear section headings detected. Organize your resume with distinct sections.")

    # Bullet consistency (max 30)
    bullets = re.findall(r"(?:^|\n)\s*[-•*]\s", text)
    if len(bullets) >= 10:
        score += 30
    elif len(bullets) >= 5:
        score += 15
        improvements.append("Use more bullet points to list responsibilities and achievements instead of paragraphs.")
    else:
        improvements.append("Resume heavily lacks bullet points. Bullet points improve ATS parsing and human readability.")
        
    if score >= 100: score = 100
    
    if score >= 80: reasons.append("Strong formatting with clear contact info and structure.")
    elif score >= 50: reasons.append("Average formatting; some organizational elements are missing.")
    else: reasons.append("Poor formatting; lacks basic structure or contact information.")
    
    return {"score": score, "reason": " ".join(reasons).strip(), "improvements": improvements}

def calculate_readability_score(text):
    score = 100
    reasons = []
    improvements = []
    
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 0]
    
    # Huge paragraphs penalty
    long_paragraphs = [p for p in paragraphs if len(p.split()) > 40 and not re.search(r"[-•*]", p)]
    if long_paragraphs:
        deduction = min(40, len(long_paragraphs) * 15)
        score -= deduction
        reasons.append(f"Found {len(long_paragraphs)} excessively long paragraph(s).")
        improvements.append("Break down large blocks of text into concise bullet points.")
        
    # Word count limits
    words = text.split()
    word_count = len(words)
    if word_count < 150:
        score -= 30
        reasons.append("Resume is too short to provide meaningful context.")
        improvements.append("Expand on your experience and projects; current resume is too brief.")
    elif word_count > 1000:
        score -= 10
        reasons.append("Resume is excessively long.")
        improvements.append("Edit down the resume to highlight only the most relevant and impactful information.")
        
    # Repeated words penalty (filler language)
    filler_words = ["responsible for", "duties included", "worked on", "helped with", "assisted in", "tasked with"]
    filler_count = sum(1 for f in filler_words if f in text.lower())
    if filler_count > 2:
        score -= 20
        reasons.append("Excessive use of passive filler language detected.")
        improvements.append("Replace passive phrases like 'responsible for' with strong action verbs.")
        
    if score < 0: score = 0
    if score > 100: score = 100
    
    if score >= 85: reasons.append("Highly readable and well-paced.")
    elif not reasons: reasons.append("Readability is acceptable.")
    
    return {"score": score, "reason": " ".join(reasons).strip(), "improvements": improvements}

def calculate_section_score(sections_dict):
    score = 0
    missing = []
    improvements = []
    
    required = ["summary", "education", "skills", "projects", "experience"]
    
    for req in required:
        if req in sections_dict and len(sections_dict[req].strip()) > 10:
            score += 20
        else:
            missing.append(req.title())
            improvements.append(f"Add a {req.title()} section to provide a complete profile.")
            
    reasons = []
    if missing:
        reasons.append(f"Missing required sections: {', '.join(missing)}.")
    else:
        reasons.append("All core sections are present.")
        
    return {"score": score, "reason": " ".join(reasons).strip(), "missing_sections": missing, "improvements": improvements}

def calculate_experience_quality(text, sections_dict):
    score = 0
    reasons = []
    improvements = []
    
    exp_text = sections_dict.get("experience", "")
    if not exp_text.strip():
        return {"score": 0, "reason": "No experience section found.", "improvements": ["Add a detailed Experience section highlighting your past roles."]}
        
    action_verbs = ["developed", "engineered", "architected", "spearheaded", "optimized", "implemented", "reduced", "increased", "designed", "managed", "led", "delivered", "integrated", "automated", "resolved", "built", "created"]
    
    bullets = re.findall(r"(?:^|\n)\s*[-•*]\s*(.+)", exp_text)
    
    if not bullets:
        return {"score": 0, "reason": "No valid experience bullet points found.", "improvements": ["Format experience descriptions as bullet points rather than paragraphs."]}
        
    # Action verbs
    verb_count = sum(1 for b in bullets if any(b.lower().startswith(v) or b.lower().split()[0] == v for v in action_verbs))
    if verb_count >= 5: score += 20
    elif verb_count >= 2: score += 10
    else: improvements.append("Start bullet points with strong action verbs (e.g., 'Developed', 'Optimized') instead of passive words.")
    
    # Quantified results
    digits = len(re.findall(r'\b\d{2,}\b', exp_text)) # numbers >= 10
    percents = len(re.findall(r'%', exp_text))
    money = len(re.findall(r'\$', exp_text))
    total_metrics = digits + percents + money
    
    if total_metrics >= 6: score += 40
    elif total_metrics >= 3: 
        score += 20
        improvements.append("Experience bullets have some metrics, but could use more quantified outcomes.")
    else:
        improvements.append("Experience bullets lack measurable outcomes. Include metrics such as users served, performance improvements, or accuracy gains.")
        
    # Bullet quality & depth (penalize short, generic bullets)
    short_bullets = [b for b in bullets if len(b.split()) < 6]
    if len(short_bullets) > 0:
        score -= min(20, len(short_bullets) * 5)
        reasons.append(f"Found {len(short_bullets)} single-line or overly brief experience entries.")
        improvements.append("Expand on brief experience bullets to explain the 'how' and 'why' behind the task.")
    else:
        score += 20  # Good depth
        
    # Technical depth in experience
    tech_keywords = ["python", "java", "javascript", "react", "sql", "aws", "docker", "api", "framework", "cloud", "agile", "c++", "node"]
    tech_matches = sum(1 for kw in tech_keywords if kw in exp_text.lower())
    if tech_matches >= 3: score += 20
    elif tech_matches > 0: score += 10
    else: improvements.append("Experience section does not mention technical tools. Ensure you include the technologies used in your roles.")
    
    # Duplicate checking
    if len(set(bullets)) < len(bullets):
        score -= 10
        improvements.append("Remove repeated bullet points in your experience section.")
    
    if score < 0: score = 0
    if score > 100: score = 100
    
    if score >= 80: reasons.append("Experience is highly impactful, well-quantified, and action-oriented.")
    elif score >= 40: reasons.append("Experience shows some depth but lacks consistent quantification or strong action verbs.")
    else: reasons.append("Experience section is weak, generic, or lacks measurable results.")
        
    return {"score": score, "reason": " ".join(reasons).strip(), "improvements": improvements}

def calculate_project_quality(text, sections_dict):
    score = 0
    reasons = []
    improvements = []
    
    proj_text = sections_dict.get("projects", "")
    if not proj_text.strip():
        return {"score": 0, "reason": "No projects found.", "improvements": ["Add a Projects section with detailed descriptions of technical projects."]}
        
    # Description quality (length/bullets)
    words = len(proj_text.split())
    if words >= 100: score += 30
    elif words >= 50: 
        score += 15
        improvements.append("Project descriptions are somewhat brief. Add more technical details.")
    else:
        improvements.append("Project descriptions are too short. Explain the problem, solution, and your specific contribution.")
        
    # Tech stack mentioned
    tech_keywords = ["using", "stack", "technologies", "built with", "developed in", "python", "javascript", "react", "node", "sql", "aws", "docker", "api"]
    has_tech = any(kw in proj_text.lower() for kw in tech_keywords)
    if has_tech: score += 30
    else: improvements.append("Explicitly state the technologies, frameworks, and languages used for each project.")
    
    # Quantified results in projects
    if len(re.findall(r'\b\d{2,}\b|%|\$', proj_text)) >= 2:
        score += 20
    else:
        improvements.append("Include measurable outcomes or scale in your projects (e.g., 'handled 10K requests', 'reduced latency by 200ms').")
        
    # Links
    if re.search(r"(github\.com|gitlab\.com|bitbucket\.org|vercel\.app|heroku|live)", proj_text.lower()):
        score += 20
    else:
        improvements.append("Add links to source code (GitHub) or live deployments for your projects.")
        
    if score > 100: score = 100
    if score < 0: score = 0
    
    if score >= 80: reasons.append("Projects are detailed, technical, and demonstrate clear outcomes.")
    elif score >= 40: reasons.append("Projects are present but lack technical depth or links.")
    else: reasons.append("Project section is weak and lacks technical descriptions.")
    
    return {"score": score, "reason": " ".join(reasons).strip(), "improvements": improvements}

def calculate_skills_quality(text, sections_dict, jd_text=None):
    score = 0
    reasons = []
    improvements = []
    
    skills_text = sections_dict.get("skills", "")
    if not skills_text.strip():
        skills_text = text
    
    text_lower = text.lower()
    
    modern_tech = [
        "python", "java", "javascript", "c++", "c#", "go", "rust", "typescript", "ruby", "php",
        "react", "angular", "vue", "django", "flask", "spring", "express", "node.js", "next.js",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "linux", "git",
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "machine learning", "pytorch", "tensorflow", "graphql", "kafka"
    ]
    
    basic_tech = ["html", "css", "word", "excel", "powerpoint", "windows", "macos", "ms office"]
    
    found_modern = list(set([kw for kw in modern_tech if kw in text_lower]))
    found_basic = list(set([kw for kw in basic_tech if kw in text_lower]))
    
    # Diversity & Relevance
    if len(found_modern) >= 8: score += 60
    elif len(found_modern) >= 4: 
        score += 30
        improvements.append("Skill diversity is average. Consider adding more modern frameworks or tools you are familiar with.")
    elif len(found_modern) > 0:
        score += 15
        improvements.append(f"Resume contains only {len(found_modern)} technical skills. Add technologies used in projects such as frameworks or databases.")
    else:
        improvements.append("No modern technical skills detected. Ensure you list specific programming languages, frameworks, and databases.")
        
    if len(found_basic) > len(found_modern):
        score -= 20
        reasons.append("Basic/outdated skills heavily outnumber modern technical skills.")
        improvements.append("Remove basic skills like 'MS Word' or 'Windows' and focus on specialized technical skills.")
        
    if jd_text:
        jd_lower = jd_text.lower()
        jd_modern = set([kw for kw in modern_tech if kw in jd_lower])
        if jd_modern:
            overlap = set(found_modern).intersection(jd_modern)
            match_percent = len(overlap) / len(jd_modern)
            if match_percent >= 0.7: score += 40
            elif match_percent >= 0.4: score += 20
            else: improvements.append(f"Missing key technologies required by the Job Description (e.g., {', '.join(list(jd_modern - set(found_modern))[:3])}).")
        else:
            score += 40 # JD has no specific tech, give points anyway
    else:
        # No JD provided, baseline points for just having skills
        if len(found_modern) >= 4: score += 40
        
    if score < 0: score = 0
    if score > 100: score = 100
    
    if score >= 80: reasons.append("Strong, diverse set of modern technical skills highly relevant to industry standards.")
    elif score >= 40: reasons.append("Acceptable skills, but could be more diverse or tailored.")
    else: reasons.append("Skills section is weak, missing, or overly generic.")
    
    return {"score": score, "reason": " ".join(reasons).strip(), "improvements": improvements}

def evaluate_resume(text, jd_text=None):
    if not text or len(text.strip()) < 10:
        return {
            "overall_score": 0,
            "breakdown": {
                "formatting": {"score": 0, "reason": "Empty or nearly empty resume.", "improvements": []},
                "section": {"score": 0, "reason": "Empty resume.", "improvements": []},
                "readability": {"score": 0, "reason": "Empty resume.", "improvements": []},
                "skills": {"score": 0, "reason": "Empty resume.", "improvements": []},
                "project": {"score": 0, "reason": "Empty resume.", "improvements": []},
                "experience": {"score": 0, "reason": "Empty resume.", "improvements": []}
            },
            "recommendations": ["Upload a complete resume with text."],
            "weak_areas": ["Entire Resume"],
            "missing_sections": ["Summary", "Education", "Skills", "Projects", "Experience"],
            "summary": "The provided resume is empty or lacks sufficient text for analysis."
        }
        
    sections_dict = extract_sections(text)
        
    formatting = calculate_formatting_score(text)
    section = calculate_section_score(sections_dict)
    readability = calculate_readability_score(text)
    skills = calculate_skills_quality(text, sections_dict, jd_text)
    project = calculate_project_quality(text, sections_dict)
    experience = calculate_experience_quality(text, sections_dict)
    
    overall = (
        formatting["score"] * 0.15 +
        section["score"] * 0.10 +
        readability["score"] * 0.15 +
        skills["score"] * 0.20 +
        project["score"] * 0.15 +
        experience["score"] * 0.25
    )
    
    all_improvements = []
    for category in [formatting, section, readability, skills, project, experience]:
        for imp in category.get("improvements", []):
            if imp not in all_improvements:
                all_improvements.append(imp)
                
    weak_areas = []
    if formatting["score"] < 50: weak_areas.append("Formatting")
    if readability["score"] < 50: weak_areas.append("Readability")
    if experience["score"] < 50: weak_areas.append("Experience Depth")
    if project["score"] < 50: weak_areas.append("Project Details")
    if skills["score"] < 50: weak_areas.append("Technical Skills")
    
    missing = section.get("missing_sections", [])
    
    summary = ""
    if overall >= 80: summary = "Excellent ATS compatibility. Your resume is well-structured and impactful."
    elif overall >= 50: summary = "Average ATS compatibility. Review the suggestions to improve your ranking."
    else: summary = "Poor ATS compatibility. Major revisions are needed to pass ATS screens."
    
    return {
        "overall_score": int(round(overall)),
        "breakdown": {
            "formatting": formatting,
            "section": section,
            "readability": readability,
            "skills": skills,
            "project": project,
            "experience": experience
        },
        "recommendations": all_improvements,
        "weak_areas": weak_areas,
        "missing_sections": missing,
        "summary": summary
    }

def calculate_career_intelligence_score(resume_text, jd_text, readiness_score):
    skills_score = calculate_skills_quality(resume_text, extract_sections(resume_text), jd_text)["score"]
    exp_score = calculate_experience_quality(resume_text, extract_sections(resume_text))["score"]
    project_score = calculate_project_quality(resume_text, extract_sections(resume_text))["score"]
    
    overall = (
        skills_score * 0.40 +
        exp_score * 0.25 +
        project_score * 0.20 +
        readiness_score * 0.15
    )
    
    return int(round(overall))


