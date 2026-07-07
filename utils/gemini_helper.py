import os
import re
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from the environment. Please add it to your .env file.")

client = genai.Client(api_key=api_key)

def strip_pii(text):
    """
    Removes emails, phone numbers, and common PII patterns from text
    to ensure data privacy before sending to AI endpoints.
    """
    if not text:
        return text
        
    # Strip Emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    text = re.sub(email_pattern, '[EMAIL]', text)
    
    # Strip Phone Numbers (various international and local formats)
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    text = re.sub(phone_pattern, '[PHONE]', text)
    
    # Strip PIN / Zip Codes
    zip_pattern = r'\b\d{5}(?:-\d{4})?\b'
    text = re.sub(zip_pattern, '[PIN]', text)
    
    return text

def clean_gemini_response(text):
    """
    Strips markdown wrappers (like ```json ... ```), trims whitespace, 
    and strictly validates the JSON response.
    """
    if not text:
        raise ValueError("AI response parsing failed. Please try again.")
        
    text = text.strip()
    
    # Handle markdown code blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
        
    if text.endswith("```"):
        text = text[:-3]
        
    text = text.strip()
    
    try:
        data = json.loads(text)
        return data
    except json.JSONDecodeError:
        # Fallback error requested in requirements
        raise ValueError("AI response parsing failed. Please try again.")

def analyze_jd_match(resume_text, jd_text):
    """
    Executes the Gemini 2.5 Flash prompt.
    Returns a validated python dictionary of the ATS analysis.
    """
    safe_resume = strip_pii(resume_text)
    safe_jd = strip_pii(jd_text)
    
    prompt = f"""
You are an expert ATS (Applicant Tracking System) and Career Coach.
Analyze the provided Resume against the provided Job Description.

CRITICAL RULES:
1. NEVER hallucinate skills, projects, or technologies.
2. ONLY use information found strictly within the Resume and Job Description.
3. Your response MUST be valid JSON. Do not include any other text.
4. "jd_required_skills" MUST ONLY contain skills explicitly stated in the Job Description.
5. "resume_existing_skills" MUST ONLY contain skills explicitly stated in the Resume.
6. "missing_skills" MUST strictly be the mathematical difference: (jd_required_skills MINUS resume_existing_skills). Do NOT fabricate missing skills.
7. For all suggestion arrays, you MUST return objects with "type" and "value".
   Allowed types: "skill", "summary", "project", "experience", "certification"

JSON FORMAT EXACTLY LIKE THIS:
{{
  "job_title": "Extracted Job Title from JD",
  "ats_score": 0,
  "jd_required_skills": ["Java", "TypeScript"],
  "resume_existing_skills": ["Python", "JavaScript"],
  "missing_skills": [
    {{"type": "skill", "value": "Java"}},
    {{"type": "skill", "value": "TypeScript"}}
  ],
  "missing_keywords": [
    {{"type": "skill", "value": "CI/CD"}}
  ],
  "interview_topics": ["Microservices", "System Design"],
  "project_gaps": [
    {{"type": "project", "value": "Built a scalable microservice architecture."}}
  ],
  "summary_improvements": [
    {{"type": "summary", "value": "Passionate software engineer with experience in Docker and Kubernetes."}}
  ],
  "experience_improvements": [
    {{"type": "experience", "value": "Quantify achievements by adding metrics like 'Improved deployment time by 20%'."}}
  ]
}}

RESUME:
{safe_resume}

JOB DESCRIPTION:
{safe_jd}
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    return clean_gemini_response(response.text)

def analyze_ats_qualitative(resume_text, jd_text=None):
    """
    Executes the Gemini 2.5 Flash prompt for qualitative ATS analysis without generating numerical scores.
    """
    safe_resume = strip_pii(resume_text)
    safe_jd = strip_pii(jd_text) if jd_text else "General Industry Standards"
    
    prompt = f"""
You are an expert ATS (Applicant Tracking System) and Career Coach.
Analyze the provided Resume for overall quality, strengths, and weaknesses. If a Job Description is provided, cross-reference against it to identify missing keywords.

CRITICAL RULES:
1. Never hallucinate skills or technologies.
2. Only use information found strictly within the Resume and Job Description.
3. DO NOT output numerical scores. The scoring is handled by a deterministic engine.
4. Your response MUST be valid JSON. Do not include any other text.

JSON FORMAT EXACTLY LIKE THIS:
{{
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "recommendations": ["rec1", "rec2"],
  "missing_keywords": ["keyword1", "keyword2"]
}}

RESUME:
{safe_resume}

JOB DESCRIPTION:
{safe_jd}
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    return clean_gemini_response(response.text)


def optimize_resume(resume_text, jd_text):
    """
    Generates an optimized resume based on the JD without hallucinating.
    """
    safe_resume = strip_pii(resume_text)
    safe_jd = strip_pii(jd_text)
    
    prompt = f"""
You are an expert Executive Resume Writer and ATS Optimizer.
Rewrite the provided Resume to perfectly match the Job Description.

STRICT RULES:
1. Do NOT create fake skills
2. Do NOT create fake projects
3. Do NOT create fake companies
4. Do NOT create fake certifications
5. Do NOT create fake experience
6. Improve wording ONLY
7. Improve ATS friendliness ONLY
8. Improve structure ONLY
9. Improve action verbs ONLY
10. Your response MUST be valid JSON.

JSON FORMAT EXACTLY LIKE THIS:
{{
  "optimized_sections": {{
    "summary": "Optimized summary text...",
    "experience": "Optimized experience bullet points...",
    "projects": "Optimized project details...",
    "skills": "Reordered and ATS optimized skills..."
  }},
  "improvements_made": ["Improved action verbs", "Enhanced project descriptions", "Added ATS Keywords"],
  "ats_improvement_score": (integer between 5 and 30 representing points gained)
}}

RESUME:
{safe_resume}

JOB DESCRIPTION:
{safe_jd}
"""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    return clean_gemini_response(response.text)

def generate_cover_letter(resume_text, jd_text, role_title, company_name):
    """
    Generates an ATS-friendly, human-sounding 3-paragraph plain-text cover letter.
    """
    safe_resume = strip_pii(resume_text)
    safe_jd = strip_pii(jd_text)
    
    prompt = f"""
You are an expert Career Coach and Executive Writer.
Write a Cover Letter for the role of "{role_title}" at "{company_name}".
Use the provided Resume and Job Description.

STRICT RULES:
1. Maximum 3 paragraphs.
2. Must reference skills from the resume.
3. Must reference requirements from the JD.
4. Professional tone, human sounding, ATS optimized.
5. Do NOT invent experience, projects, certifications, or achievements.
6. Return Plain Text ONLY. NO markdown formatting. NO JSON. NO intro/outro like "Here is the cover letter:". Just the letter itself.

RESUME:
{safe_resume}

JOB DESCRIPTION:
{safe_jd}
"""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    text = response.text.strip()
    return text


def generate_skill_gap_analysis(resume_text, jd_text):
    """
    Phase 4: Career Intelligence Engine
    Analyzes the depth of the skill gap and prepares the user for the interview.
    """
    safe_resume = strip_pii(resume_text)
    safe_jd = strip_pii(jd_text)
    
    prompt = f"""
You are an expert Technical Interviewer and Career Coach.
Analyze the provided Resume against the Job Description to identify critical gaps and interview risks.

STRICT RULES:
1. Rank missing skills by highest impact/priority first.
2. Generate an Interview Readiness Score (0-100) representing how likely they are to pass a technical interview right now.
3. Be brutally honest about high-risk areas.
4. Your response MUST be valid JSON.

JSON FORMAT EXACTLY LIKE THIS:
{{
  "readiness_score": 62,
  "priority_skills": ["Docker", "AWS", "Kubernetes"],
  "likely_interview_topics": ["System Design", "Container Orchestration", "CI/CD Pipelines"],
  "high_risk_areas": ["Lack of cloud infrastructure experience", "Missing production containerization"],
  "questions_to_prepare": [
    "Explain the difference between a virtual machine and a Docker container.",
    "How would you deploy a stateless microservice to Kubernetes?"
  ]
}}

RESUME:
{safe_resume}

JOB DESCRIPTION:
{safe_jd}
"""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    return clean_gemini_response(response.text)

def generate_learning_roadmap(priority_skills, resume_text, jd_text, ats_score=None, readiness_score=None, project_gaps=None, interview_topics=None):
    """
    Phase 4: Career Intelligence Engine
    Generates a dynamic learning roadmap based on missing skills, ATS score, and readiness score.
    """
    skills_list = ", ".join(priority_skills) if priority_skills else "General technical skills"
    safe_resume = strip_pii(resume_text)
    safe_jd = strip_pii(jd_text)
    
    project_gaps_str = ", ".join(project_gaps) if project_gaps else "None explicitly identified"
    interview_topics_str = ", ".join(interview_topics) if interview_topics else "General technical topics"
    
    prompt = f"""
You are an expert Technical Mentor and Career Coach.
Create a structured, dynamic learning roadmap to master the missing skills and close the gaps between the student's resume and the job description.

CONTEXT:
- ATS Match Score: {ats_score if ats_score else 'Unknown'}%
- Interview Readiness Score: {readiness_score if readiness_score else 'Unknown'}%
- Primary Missing Skills: {skills_list}
- Missing Projects/Technologies: {project_gaps_str}
- Interview Weaknesses/Topics: {interview_topics_str}

STRICT RULES:
1. Generate dynamic phases (minimum 3 phases, maximum 8 phases). The number of phases MUST depend on the size of the gap (e.g. lower ATS/Readiness scores require more phases).
2. DO NOT use "Week 1", "Week 2", etc. Use descriptive names like "Phase 1 - Foundation Building", "Phase 2 - Skill Development", etc.
3. The roadmap MUST be personalized to the student's existing background.
4. Your response MUST be valid JSON.

JSON FORMAT EXACTLY LIKE THIS:
{{
  "target_company": "Company Name extracted from JD, or 'Unknown'",
  "phases": [
    {{
      "phase": "Phase 1 - Foundation Building",
      "objectives": ["Understand core concepts of X"],
      "skills": ["Skill 1", "Skill 2"],
      "activities": ["Read documentation on X", "Complete interactive tutorial"],
      "deliverables": ["A simple functional script"],
      "expected_outcome": "Solid foundational knowledge"
    }},
    {{
      "phase": "Phase 2 - Core Development",
      "objectives": ["..."],
      "skills": ["..."],
      "activities": ["..."],
      "deliverables": ["..."],
      "expected_outcome": "..."
    }}
  ]
}}

RESUME (Student Background):
{safe_resume}

JOB DESCRIPTION:
{safe_jd}
"""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    return clean_gemini_response(response.text)

def validate_entities(entity_type, values):
    """
    Validates an array of strings (skills, projects, or certificates) to check if they are real professional terms
    or just random keyboard smashes/gibberish.
    Returns a dictionary mapping each value to a boolean: { "value": True/False }
    """
    if not values:
        return {}
        
    prompt = f"""
    You are a professional profile validation assistant.
    I will provide a list of '{entity_type}' names entered by a user.
    Your job is to strictly determine if each entry is a plausible, real-world {entity_type} OR if it is random gibberish/keyboard smashes (e.g., 'scsnsbvb', 'asdf', '123123').
    
    A '{entity_type}' name does not have to be famous, it just has to be linguistically coherent and plausible in a professional context. 
    If it's just random letters or inappropriate garbage, mark it false.
    
    Return a strictly formatted JSON object where keys are the exact input strings and values are boolean true/false.
    
    Inputs:
    {json.dumps(values)}
    
    JSON Output:
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Validation failed: {e}")
        # Fail open if Gemini is down so we don't completely break the UI
        return {val: True for val in values}
