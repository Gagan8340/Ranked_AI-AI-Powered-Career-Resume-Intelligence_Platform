import fitz  # PyMuPDF
import docx

def extract_resume_text(file_stream, file_ext):
    """
    Extracts text from a PDF or DOCX file stream.
    Returns (extracted_text, is_scanned)
    
    file_stream: Werkzeug FileStorage or BytesIO
    file_ext: 'pdf' or 'docx'
    """
    text = ""
    is_scanned = False
    
    try:
        # Read the stream content
        stream_content = file_stream.read()
        
        # VERY IMPORTANT: Reset the stream pointer back to 0 
        # so Cloudinary or other processors can read it again afterwards!
        file_stream.seek(0)

        if file_ext == 'pdf':
            # Load PDF from memory bytes
            doc = fitz.open(stream=stream_content, filetype="pdf")
            for page in doc:
                text += page.get_text()
            doc.close()
            
        elif file_ext == 'docx':
            from io import BytesIO
            doc = docx.Document(BytesIO(stream_content))
            for para in doc.paragraphs:
                text += para.text + "\n"
                
        # Clean up whitespace
        text = text.strip()
        
        # Scanned PDF Detection:
        # If the extracted text is less than 100 characters, it's highly likely
        # an image-based/scanned PDF without an OCR text layer.
        if len(text) < 100:
            is_scanned = True
            
        return text, is_scanned
        
    except Exception as e:
        raise Exception(f"Failed to parse resume: {str(e)}")


def parse_resume_for_profile_deterministic(text):
    """
    Deterministically parses raw resume text into structured fields for the builder profile.
    Replaces the previous Gemini-based parsing to ensure offline capability and stability.
    """
    from utils.ats_engine import extract_sections
    import re
    
    sections = extract_sections(text)
    
    # 1. Summary
    summary = sections.get("summary", "").strip()
    if not summary:
        # Fallback: grab first few lines as summary if no section header found
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        summary = " ".join(lines[:3]) if lines else ""
    
    # 2. Skills
    skills_text = sections.get("skills", "")
    skills_raw = re.split(r'[,\n|]', skills_text)
    skills = [s.strip(" \t-•*") for s in skills_raw if s.strip(" \t-•*")]
    skills = [s for s in skills if 1 < len(s) < 50]
    
    # 3. Achievements
    achievements_text = sections.get("achievements", "")
    achievements = [a.strip(" \t-•*") for a in achievements_text.split('\n') if len(a.strip(" \t-•*")) > 5]
    
    # 4. Education
    edu_text = sections.get("education", "")
    education = [e.strip(" \t-•*") for e in edu_text.split('\n') if len(e.strip(" \t-•*")) > 5]
    
    # 5. Experience
    exp_text = sections.get("experience", "")
    experience = [e.strip(" \t-•*") for e in exp_text.split('\n') if len(e.strip(" \t-•*")) > 5]
    
    # 6. Projects
    projects = []
    proj_text = sections.get("projects", "")
    proj_lines = [p.strip(" \t-•*") for p in proj_text.split('\n') if len(p.strip(" \t-•*")) > 5]
    
    for line in proj_lines:
        if len(line) > 10:
            projects.append({
                "project_name": line[:50] + ("..." if len(line)>50 else ""),
                "description": line,
                "tech_stack": "",
                "github_url": "",
                "live_url": ""
            })
            if len(projects) >= 5:
                break
                
    # 7. Certifications
    certs = []
    certs_text = sections.get("certifications", "")
    certs_lines = [c.strip(" \t-•*") for c in certs_text.split('\n') if len(c.strip(" \t-•*")) > 5]
    for line in certs_lines:
        certs.append({
            "name": line[:100],
            "issuer": "",
            "issue_date": "",
            "certificate_url": ""
        })
        if len(certs) >= 5:
            break
            
    # 8. Links
    linkedin = ""
    github = ""
    portfolio = ""
    
    linkedin_match = re.search(r'(https?://(?:www\.)?linkedin\.com/[^\s]+)', text)
    if linkedin_match:
        linkedin = linkedin_match.group(1)
        
    github_match = re.search(r'(https?://(?:www\.)?github\.com/[^\s]+)', text)
    if github_match:
        github = github_match.group(1)
        
    return {
        "professional_summary": summary,
        "skills": skills,
        "achievements": achievements,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certifications": certs,
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio
    }
