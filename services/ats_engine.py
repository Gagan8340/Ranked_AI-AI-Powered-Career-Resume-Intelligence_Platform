"""
ATS Score Engine — Fully Algorithmic, Zero AI Dependency
=========================================================
Every score is deterministic and explainable.
No fake values. No random padding. No AI hallucination.

Score = sum of all component scores, each computed from
real presence/absence/quality signals in the resume text.

Author: Built for your ranked AI platform
"""

import re
import math
import logging
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
#  WEIGHTS  (research-backed, total = 100)
# ─────────────────────────────────────────────
WEIGHTS = {
    "contact_info":          5,
    "professional_summary":  8,
    "skills_section":       10,
    "experience_section":   25,
    "education_section":     7,
    "projects_section":      5,
    "certifications":        5,
    "ats_formatting":       15,
    "keyword_coverage":     20,
}
assert sum(WEIGHTS.values()) == 100, "Weights must sum to 100"


# ─────────────────────────────────────────────
#  DATA CLASSES
# ─────────────────────────────────────────────
@dataclass
class ComponentResult:
    """
    Score result for one component.
    raw_score  : 0.0–1.0 (percentage of component earned)
    weighted   : raw_score × weight  (actual points toward 100)
    breakdown  : list of (signal_name, earned, max, note)
    """
    name: str
    weight: int
    raw_score: float          # 0.0 → 1.0
    weighted: float           # raw_score × weight
    breakdown: list = field(default_factory=list)
    feedback: list = field(default_factory=list)


@dataclass
class ATSResult:
    total_score: int          # 0–100, rounded integer
    grade: str                # A / B / C / D / F
    grade_label: str          # human label
    components: dict          # component_name → ComponentResult
    keyword_matches: list     # matched keywords from JD
    keyword_missing: list     # missing keywords from JD
    top_issues: list          # top 3 actionable fixes
    parsing_warnings: list    # structural issues found


# ─────────────────────────────────────────────
#  SIGNAL PATTERNS
# ─────────────────────────────────────────────

# Section header detection
SECTION_PATTERNS = {
    "summary":        r"^[\W_]*(?:\d+\.?\s*)?(professional\s+summary|summary|objective|profile|about\s+me|career\s+objective|executive\s+summary)(?:[\W_]*:|[\W_]*(?=\n|$))",
    "skills":         r"^[\W_]*(?:\d+\.?\s*)?(skills|skills\s+summary|technical\s+skills|core\s+competencies|competencies|expertise|areas\s+of\s+expertise|technologies|it\s+skills|skills\s+(?:and|&)\s+expertise|technical\s+expertise)(?:[\W_]*:|[\W_]*(?=\n|$))",
    "experience":     r"^[\W_]*(?:\d+\.?\s*)?(experience|work\s+experience|employment|work\s+history|professional\s+experience|career|internships?|volunteering|professional\s+background)(?:[\W_]*:|[\W_]*(?=\n|$))",
    "education":      r"^[\W_]*(?:\d+\.?\s*)?(education|academic|qualifications?|degree|university|college|academic\s+background|educational\s+background)(?:[\W_]*:|[\W_]*(?=\n|$))",
    "projects":       r"^[\W_]*(?:\d+\.?\s*)?(projects|project\s+experience|personal\s+projects|key\s+projects|portfolio|academic\s+projects)(?:[\W_]*:|[\W_]*(?=\n|$))",
    "certifications": r"^[\W_]*(?:\d+\.?\s*)?(certifications?|certificates?|credentials?|licenses?|accreditations?)(?:[\W_]*:|[\W_]*(?=\n|$))",
}

# Contact field patterns
EMAIL_RE    = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE    = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w\-]+", re.I)
GITHUB_RE   = re.compile(r"github\.com/[\w\-]+", re.I)
LOCATION_RE = re.compile(r"\b([A-Z][a-z]+(?:[\s,]+[A-Z][a-zA-Z]+){0,3}(?:,\s*[A-Z]{2})?)\b")

# Date pattern (for experience entries)
DATE_RE = re.compile(
    r"\b(\d{4})\b"                              # 2023
    r"|(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4})\b"  # Jan 2023
    r"|(present|current|now)\b",                # Present
    re.I
)

# Action verbs (strong resume indicators)
ACTION_VERBS = {
    "led", "built", "developed", "designed", "implemented", "architected",
    "managed", "created", "launched", "delivered", "optimized", "improved",
    "increased", "reduced", "achieved", "deployed", "automated", "engineered",
    "collaborated", "coordinated", "analyzed", "established", "transformed",
    "directed", "spearheaded", "streamlined", "generated", "mentored",
    "scaled", "migrated", "integrated", "resolved", "negotiated", "produced",
}

# Quantification patterns (numbers in bullet points)
QUANT_RE = re.compile(
    r"\d+\s*(%|percent|x\b|k\b|m\b|billion|million|thousand|users|customers|"
    r"teams?|engineers?|projects?|hrs?|hours?|days?|weeks?|months?|years?)",
    re.I
)

# ATS-hostile formatting signals
TABLE_RE       = re.compile(r"\|.+\|.+\|")          # markdown/ascii tables
MULTI_COL_RE   = re.compile(r"\t{2,}|  {6,}")       # suspicious whitespace
SPECIAL_CHAR_RE = re.compile(r"[●■▪◆►▸→✓✔★☆•]")     # fancy bullets
HEADER_BOX_RE  = re.compile(r"^={3,}|-{3,}$", re.M) # decorative dividers

# Consistent date format checker
DATE_FORMAT_RE = [
    re.compile(r"\b\d{4}\s*[-–]\s*\d{4}\b"),        # 2020-2023
    re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b", re.I),
    re.compile(r"\b\d{1,2}/\d{4}\b"),               # 01/2023
]


# ─────────────────────────────────────────────
#  HELPER UTILITIES
# ─────────────────────────────────────────────

def _clean(text: str) -> str:
    """Normalise whitespace, lowercase for matching."""
    return re.sub(r"\s+", " ", text.strip())


def _find_section(text: str, key: str) -> Optional[str]:
    """
    Extract text from a resume section.
    Returns the block from the section header to the next section header.
    """
    pattern = SECTION_PATTERNS.get(key, "")
    if not pattern:
        return None

    lower = text.lower()
    match = re.search(pattern, lower, re.MULTILINE)
    if not match:
        return None

    # Find next section boundary (any other section header at the start of a line)
    remaining = text[match.end():]
    remaining_lower = remaining.lower()
    
    next_match_start = len(remaining)
    for k, p in SECTION_PATTERNS.items():
        if k == key:
            continue
        m = re.search(p, remaining_lower, re.MULTILINE)
        if m and m.start() < next_match_start:
            next_match_start = m.start()

    if next_match_start < len(remaining):
        return remaining[:next_match_start].strip()
    return remaining.strip()


def _count_bullets(text: str) -> int:
    """Count bullet-point lines in a section."""
    return len(re.findall(r"^\s*[-•*▪►]\s+\S", text, re.M))


def _extract_years_experience(text: str) -> int:
    """Best-effort estimate of years of experience from date ranges."""
    years = re.findall(r"\b(20\d{2}|19\d{2})\b", text)
    if len(years) >= 2:
        years_int = sorted([int(y) for y in years])
        return years_int[-1] - years_int[0]
    return 0


def _grade(score: int) -> tuple:
    if score >= 85: return "A", "Excellent — ATS ready"
    if score >= 70: return "B", "Good — minor fixes needed"
    if score >= 55: return "C", "Fair — several improvements needed"
    if score >= 40: return "D", "Weak — significant gaps found"
    return "F", "Poor — major rework required"


# ─────────────────────────────────────────────
#  COMPONENT SCORERS
# ─────────────────────────────────────────────

def score_contact_info(text: str) -> ComponentResult:
    """
    5 signals, 1 point each → 5 max
    Email, Phone, LinkedIn, Location, (GitHub or Portfolio bonus)
    """
    w = WEIGHTS["contact_info"]
    bd = []
    feedback = []

    has_email    = bool(EMAIL_RE.search(text))
    has_phone    = bool(PHONE_RE.search(text[:500]))   # phone usually near top
    has_linkedin = bool(LINKEDIN_RE.search(text))
    has_location = bool(re.search(r"\b[A-Z][a-z]+,\s*[A-Z]{2}\b|\b[A-Z][a-z]+,\s*[A-Z][a-z]+\b", text[:300]))
    has_github   = bool(GITHUB_RE.search(text))

    earned = sum([has_email, has_phone, has_linkedin, has_location, has_github])
    max_pts = 5

    bd.append(("Email",    int(has_email),    1, "" if has_email    else "Add your email address"))
    bd.append(("Phone",    int(has_phone),    1, "" if has_phone    else "Add a contact phone number"))
    bd.append(("LinkedIn", int(has_linkedin), 1, "" if has_linkedin else "Add your LinkedIn URL"))
    bd.append(("Location", int(has_location), 1, "" if has_location else "Add city, state/country"))
    bd.append(("GitHub",   int(has_github),   1, "" if has_github   else "GitHub/portfolio URL adds credibility"))

    if not has_email:
        feedback.append("Missing email — critical contact field")
    if not has_phone:
        feedback.append("Missing phone number")
    if not has_linkedin:
        feedback.append("Add LinkedIn profile URL")

    raw = earned / max_pts
    return ComponentResult("contact_info", w, raw, raw * w, bd, feedback)


def score_professional_summary(text: str) -> ComponentResult:
    """
    Checks: section exists, word count 40–120, keyword density signal.
    """
    w = WEIGHTS["professional_summary"]
    bd = []
    feedback = []

    section = _find_section(text, "summary")
    exists = section is not None and len(section.strip()) > 20

    if not exists:
        bd.append(("Section present", 0, 3, "Add a Professional Summary section"))
        feedback.append("No professional summary detected — add 2–4 sentences at the top")
        return ComponentResult("professional_summary", w, 0.0, 0.0, bd, feedback)

    words = section.split()
    word_count = len(words)

    # Word count score: ideal 20–150 words
    if 20 <= word_count <= 150:
        wc_score = 3
    elif 10 <= word_count < 20 or 150 < word_count <= 200:
        wc_score = 2
        feedback.append(f"Summary is {'too short' if word_count < 20 else 'too long'} ({word_count} words, ideal: 20–150)")
    else:
        wc_score = 1
        feedback.append(f"Summary has {word_count} words — rewrite to 20–150 words")

    # Action verbs in summary
    summary_lower = section.lower()
    verbs_found = [v for v in ACTION_VERBS if v in summary_lower]
    verb_score = min(2, len(verbs_found))

    # Numbers/achievements in summary (bonus signal)
    has_quant = bool(QUANT_RE.search(section))
    quant_score = 1 if has_quant else 0
    if not has_quant:
        feedback.append("Add at least one quantified achievement to your summary")

    total_earned = wc_score + verb_score + quant_score
    total_max = 6

    bd.append(("Section present", 1, 1, ""))
    bd.append(("Word count (20–150)", wc_score, 3, f"{word_count} words"))
    bd.append(("Action verbs", verb_score, 2, f"Found: {', '.join(verbs_found[:3]) if verbs_found else 'none'}"))
    bd.append(("Quantified result", quant_score, 1, "Number with impact found" if has_quant else "Add metrics"))

    raw = total_earned / total_max
    return ComponentResult("professional_summary", w, raw, raw * w, bd, feedback)


def score_skills_section(text: str) -> ComponentResult:
    """
    Checks: section present, skill count, no generic fluff skills.
    """
    w = WEIGHTS["skills_section"]
    bd = []
    feedback = []

    section = _find_section(text, "skills")
    exists = section is not None and len(section.strip()) > 10

    if not exists:
        bd.append(("Section present", 0, 4, "Add a Skills section"))
        feedback.append("No skills section found — ATS specifically looks for this section")
        return ComponentResult("skills_section", w, 0.0, 0.0, bd, feedback)

    # Count distinct skills (comma/pipe/newline separated items)
    skill_items = re.split(r"[,|\n•\-]", section)
    skill_items = [s.strip() for s in skill_items if len(s.strip()) > 1]
    skill_count = len(skill_items)

    # Skill count score: 5–50 is ideal
    if 5 <= skill_count <= 50:
        count_score = 3
    elif 3 <= skill_count < 5:
        count_score = 2
        feedback.append(f"Only {skill_count} skills listed — aim for 5–50 specific skills")
    elif skill_count > 50:
        count_score = 2
        feedback.append(f"{skill_count} skills is too many — trim to 50 most relevant")
    else:
        count_score = 1
        feedback.append("Very few skills listed — add more specific technical and soft skills")

    # Fluff skill check (penalise vague entries)
    fluff = {"ms office", "internet", "typing", "hardworking"}
    section_lower = section.lower()
    fluff_found = [f for f in fluff if f in section_lower]
    fluff_score = 1 if not fluff_found else 1 # No strict penalty
    if fluff_found:
        feedback.append(f"Consider replacing vague skills like '{fluff_found[0]}' with specific ones")

    total_earned = 1 + count_score + fluff_score   # 1 for presence
    total_max = 5

    bd.append(("Section present", 1, 1, ""))
    bd.append(("Skill count", count_score, 3, f"{skill_count} skills detected"))
    bd.append(("No filler skills", fluff_score, 1, "Clean" if not fluff_found else f"Found: {', '.join(fluff_found)}"))

    raw = total_earned / total_max
    return ComponentResult("skills_section", w, raw, raw * w, bd, feedback)


def score_experience_section(text: str) -> ComponentResult:
    """
    Highest-weight component. Checks:
    - Section present
    - Number of roles
    - Date completeness (all entries have dates)
    - Action verb usage
    - Quantified achievements (numbers with impact)
    - Reverse chronological order signal
    """
    w = WEIGHTS["experience_section"]
    bd = []
    feedback = []

    section = _find_section(text, "experience")
    exists = section is not None and len(section.strip()) > 50

    if not exists:
        bd.append(("Section present", 0, 6, "No experience section found"))
        feedback.append("No experience section found — this is the highest-weighted component")
        return ComponentResult("experience_section", w, 0.0, 0.0, bd, feedback)

    # Role count (headings or company-like patterns)
    role_patterns = re.findall(
        r"\b(engineer|developer|manager|analyst|designer|director|"
        r"lead|specialist|consultant|associate|intern|coordinator)\b",
        section, re.I
    )
    role_count = min(len(role_patterns), 8)  # cap for sanity

    # Date presence in experience
    date_hits = DATE_RE.findall(section)
    date_score = min(3, len(date_hits))

    # Action verbs
    section_lower = section.lower()
    verbs_found = [v for v in ACTION_VERBS if v in section_lower]
    verb_score = min(3, len(verbs_found))
    if len(verbs_found) < 3:
        feedback.append(f"Use stronger action verbs — found only {len(verbs_found)} (e.g. 'built', 'led', 'delivered')")

    # Quantified results
    quant_hits = QUANT_RE.findall(section)
    quant_count = len(quant_hits)
    if quant_count >= 1:
        quant_score = 3
    else:
        quant_score = 0
        feedback.append("No quantified results found — add numbers (e.g. 'reduced load time by 40%')")

    # Bullet point usage
    bullet_count = _count_bullets(section)
    bullet_score = 2 if bullet_count > 0 else 0
    if bullet_count == 0:
        feedback.append("Use bullet points in your experience section for ATS parsing")

    total_earned = 1 + date_score + verb_score + quant_score + bullet_score
    total_max = 12

    bd.append(("Section present",    1,            1,  ""))
    bd.append(("Date completeness",  date_score,   3,  f"{len(date_hits)} date references found"))
    bd.append(("Action verbs",       verb_score,   3,  f"{len(verbs_found)} verbs: {', '.join(list(verbs_found)[:4])}"))
    bd.append(("Quantified results", quant_score,  3,  f"{quant_count} metrics found"))
    bd.append(("Bullet usage",       bullet_score, 2,  f"{bullet_count} bullet points detected"))

    raw = total_earned / total_max
    return ComponentResult("experience_section", w, raw, raw * w, bd, feedback)


def score_education(text: str) -> ComponentResult:
    """
    Checks: section present, institution, degree, year.
    """
    w = WEIGHTS["education_section"]
    bd = []
    feedback = []

    section = _find_section(text, "education")
    exists = section is not None and len(section.strip()) > 20

    if not exists:
        bd.append(("Section present", 0, 3, "Add an Education section"))
        feedback.append("No education section found")
        return ComponentResult("education_section", w, 0.0, 0.0, bd, feedback)

    # Check for degree keywords
    degree_re = re.compile(
        r"\b(bachelor|master|phd|doctorate|b\.?s\.?|m\.?s\.?|b\.?e\.?|m\.?e\.?|"
        r"b\.?tech|m\.?tech|mba|associate|diploma|certificate|b\.?sc|m\.?sc)\b", re.I
    )
    has_degree = bool(degree_re.search(section))

    # Check for graduation year
    has_year = bool(re.search(r"\b(20\d{2}|19\d{2})\b", section))

    # Check for institution name (simple heuristic: capitalized words)
    has_institution = bool(re.search(r"\b[A-Z][a-z]+ (University|College|Institute|School|Academy)\b", section))

    if not has_degree:
        feedback.append("Degree name not clearly detected — spell it out (e.g. 'Bachelor of Science')")
    if not has_year:
        feedback.append("Add graduation year to your education entry")

    deg_score  = 1 if has_degree else 0
    year_score = 1 if has_year else 0
    inst_score = 1 if has_institution else 0

    total_earned = 1 + deg_score + year_score + inst_score
    total_max = 4

    bd.append(("Section present",   1,          1, ""))
    bd.append(("Degree name",       deg_score,  1, "Found" if has_degree else "Not detected"))
    bd.append(("Graduation year",   year_score, 1, "Found" if has_year   else "Missing"))
    bd.append(("Institution name",  inst_score, 1, "Found" if has_institution else "Add university/college name"))

    raw = total_earned / total_max
    return ComponentResult("education_section", w, raw, raw * w, bd, feedback)


def score_projects(text: str) -> ComponentResult:
    """
    Checks: section present, at least 1 project, tech stack mentioned, impact.
    """
    w = WEIGHTS["projects_section"]
    bd = []
    feedback = []

    section = _find_section(text, "projects")
    exists = section is not None and len(section.strip()) > 30

    if not exists:
        bd.append(("Section present", 0, 3, "No Projects section (Optional)"))
        return ComponentResult("projects_section", w, 0.8, 0.8 * w, bd, ["No projects section — add relevant projects if you lack experience"])

    # Tech stack detection
    tech_re = re.compile(
        r"\b(python|javascript|react|node|java|c\+\+|sql|aws|docker|kubernetes|"
        r"django|flask|tensorflow|pytorch|mongodb|postgresql|redis|vue|angular|"
        r"typescript|rust|go|swift|kotlin|ruby|rails|spring|linux|git)\b", re.I
    )
    tech_hits = tech_re.findall(section)
    tech_score = min(2, len(set(tech_hits)))

    has_impact = bool(QUANT_RE.search(section))
    impact_score = 1 if has_impact else 0

    if not tech_hits:
        feedback.append("List the technologies used in each project")
    if not has_impact:
        feedback.append("Add project outcomes/impact with numbers where possible")

    total_earned = 1 + tech_score + impact_score
    total_max = 4

    bd.append(("Section present",    1,            1, ""))
    bd.append(("Tech stack listed",  tech_score,   2, f"Found: {', '.join(set(tech_hits))[:50]}" if tech_hits else "None detected"))
    bd.append(("Project impact",     impact_score, 1, "Quantified impact found" if has_impact else "No measurable impact"))

    raw = total_earned / total_max
    return ComponentResult("projects_section", w, raw, raw * w, bd, feedback)


def score_certifications(text: str) -> ComponentResult:
    """
    Checks: section or cert mentions, full name + acronym, issuer, date.
    """
    w = WEIGHTS["certifications"]
    bd = []
    feedback = []

    section = _find_section(text, "certifications")

    # Also search whole text for cert keywords even if no formal section
    cert_keywords = re.compile(
        r"\b(certified|certification|certificate|aws\s+certified|pmp|cpa|cfa|"
        r"comptia|cisco|cissp|ccna|gcp|azure\s+certified|google\s+certified|"
        r"scrum\s+master|csm|six\s+sigma|itil|togaf)\b", re.I
    )
    cert_in_text = cert_keywords.findall(text)

    if not section and not cert_in_text:
        bd.append(("Certifications present", 0, 3, "No certifications found (Optional)"))
        return ComponentResult("certifications", w, 0.8, 0.8 * w, bd,
                               ["No certifications section — this section is optional but valuable"])

    search_text = section if section else text
    has_date  = bool(re.search(r"\b(20\d{2}|19\d{2})\b", search_text))
    has_name  = len(cert_in_text) > 0
    has_issuer = bool(re.compile(
        r"\b(amazon|microsoft|google|pmi|cisco|isaca|comptia|isc2|axelos|scrum\.org)\b", re.I
    ).search(search_text))

    if not has_date:
        feedback.append("Add issue/expiry dates to certifications")
    if not has_issuer:
        feedback.append("List the certifying body (e.g. 'Amazon Web Services')")

    name_score   = 1 if has_name   else 0
    date_score   = 1 if has_date   else 0
    issuer_score = 1 if has_issuer else 0

    total_earned = name_score + date_score + issuer_score
    total_max = 3

    bd.append(("Cert name detected",  name_score,   1, f"Found: {', '.join(cert_in_text[:3])}" if cert_in_text else "None"))
    bd.append(("Date present",        date_score,   1, "Found" if has_date   else "Missing"))
    bd.append(("Issuer mentioned",    issuer_score, 1, "Found" if has_issuer else "Missing"))

    raw = total_earned / total_max if total_max > 0 else 0
    return ComponentResult("certifications", w, raw, raw * w, bd, feedback)


def score_ats_formatting(text: str) -> ComponentResult:
    """
    ATS formatting — penalty-based.
    Start at full score, deduct for each detected problem.
    Problems: tables, multi-column layout, special chars, inconsistent dates,
    missing section headers, very long lines, no clear structure.
    """
    w = WEIGHTS["ats_formatting"]
    bd = []
    feedback = []

    deductions = 0
    max_deductions = 4

    # Tables / ASCII grids
    has_table = bool(TABLE_RE.search(text))
    if has_table:
        deductions += 2
        feedback.append("Remove tables — ATS systems cannot reliably parse tabular content")
    bd.append(("No tables", 0 if has_table else 1, 1, "Table detected — remove it" if has_table else "Clean"))

    # Special/fancy bullets (Relaxed: Modern ATS handles these fine)
    fancy_bullets = SPECIAL_CHAR_RE.findall(text)
    has_fancy = len(fancy_bullets) > 3
    if has_fancy:
        feedback.append("Consider replacing special bullet symbols (●, ■, ►) with standard hyphens if applying to very old systems.")
    bd.append(("Standard bullets", 1, 1, f"Found {len(fancy_bullets)} special chars (Allowed)" if has_fancy else "Clean"))

    # Inconsistent date formats
    date_format_counts = [len(p.findall(text)) for p in DATE_FORMAT_RE]
    formats_used = sum(1 for c in date_format_counts if c > 0)
    inconsistent_dates = formats_used > 2
    if inconsistent_dates:
        deductions += 1
        feedback.append("Use consistent date formats (e.g. 'Jan 2022 – Mar 2024')")
    bd.append(("Consistent dates", 0 if inconsistent_dates else 1, 1,
               f"{formats_used} date formats detected" if inconsistent_dates else "Consistent"))

    # Section headers present (at least 3 standard ones)
    headers_found = sum(1 for k, p in SECTION_PATTERNS.items() if re.search(p, text.lower(), re.MULTILINE))
    missing_headers = headers_found < 3
    if missing_headers:
        deductions += 1
        feedback.append(f"Only {headers_found} standard section headers found — use clear labels like 'Experience', 'Education', 'Skills'")
    bd.append(("Clear section headers", 0 if missing_headers else 1, 1,
               f"{headers_found} headers found"))

    # Excessive whitespace / multi-column hint
    has_multi_col = bool(MULTI_COL_RE.search(text))
    if has_multi_col:
        deductions += 1
        feedback.append("Avoid multi-column layouts — use single-column format for best ATS compatibility")
    bd.append(("Single column", 0 if has_multi_col else 1, 1,
               "Multi-column layout detected" if has_multi_col else "Clean"))

    # Resume length check (words)
    word_count = len(text.split())
    too_short = word_count < 100
    too_long  = word_count > 1800
    if too_short:
        deductions += 1
        feedback.append(f"Resume is very short ({word_count} words) — add more detail")
    elif too_long:
        deductions += 1
        feedback.append(f"Resume is very long ({word_count} words) — aim for 400–800 words")
    bd.append(("Resume length", 0 if (too_short or too_long) else 1, 1,
               f"{word_count} words — ideal range 100–1800" if (too_short or too_long) else f"{word_count} words ✓"))

    earned = max(0, max_deductions - deductions)
    raw = earned / max_deductions
    return ComponentResult("ats_formatting", w, raw, raw * w, bd, feedback)


def score_keyword_coverage(text: str, job_description: str = "") -> ComponentResult:
    """
    Most important component. Compares resume to job description.
    If no JD provided, scores based on general professional vocabulary density.
    
    Scoring:
    - With JD:    (matched_keywords / total_jd_keywords) with placement bonus
    - Without JD: keyword density + professional vocabulary score
    """
    w = WEIGHTS["keyword_coverage"]
    bd = []
    feedback = []
    matched = []
    missing = []

    if job_description and len(job_description.strip()) > 50:
        # ── MODE 1: Job description provided ──────────────────────
        jd_clean   = job_description.lower()
        text_lower = text.lower()

        # Extract meaningful keywords from JD (skip stopwords)
        stopwords = {
            "the", "and", "for", "are", "you", "with", "this", "that", "will",
            "have", "your", "from", "they", "been", "their", "has", "more",
            "can", "our", "not", "but", "all", "one", "who", "its", "any",
            "was", "were", "may", "also", "such", "each", "both", "must",
            "what", "about", "would", "should", "could", "other", "into",
            "than", "then", "these", "those", "some", "most", "well", "when",
            "where", "while", "which", "after", "before", "over", "under",
        }

        # Pull noun phrases / skill-like tokens from JD
        jd_tokens = re.findall(r"\b[a-z][a-z0-9\+\#\.]{2,}\b", jd_clean)
        jd_keywords = [
            t for t in set(jd_tokens)
            if t not in stopwords and len(t) > 2
        ]

        # Weight keywords by position in JD (title/requirements = more important)
        # Simple proxy: first 30% of JD is requirements, rest is nice-to-have
        jd_split = int(len(jd_clean) * 0.35)
        critical_text = jd_clean[:jd_split]

        for kw in jd_keywords:
            in_resume   = kw in text_lower
            is_critical = kw in critical_text
            weight_mult = 1.5 if is_critical else 1.0

            if in_resume:
                # Check placement: keywords in summary/experience = higher value
                in_summary    = bool(_find_section(text, "summary") and kw in (_find_section(text, "summary") or "").lower())
                in_experience = bool(_find_section(text, "experience") and kw in (_find_section(text, "experience") or "").lower())
                placement_bonus = 0.2 if (in_summary or in_experience) else 0
                matched.append((kw, weight_mult, placement_bonus))
            else:
                missing.append((kw, is_critical))

        total_possible = sum(1.0 + (0.5 if kw in critical_text else 0) for kw in jd_keywords)
        total_earned = sum(
            (base + bonus) for (_, base, bonus) in matched
        )

        if total_possible > 0:
            # Curve the score: hitting ~40% of all non-stopword JD vocabulary is an excellent match
            raw = min(1.0, (total_earned / total_possible) * 2.5)
        else:
            raw = 0.0

        # Feedback
        critical_missing = [kw for kw, is_crit in missing if is_crit]
        if critical_missing:
            feedback.append(f"Critical keywords missing: {', '.join(critical_missing[:5])}")
        if len(missing) > len(matched):
            feedback.append(f"{len(missing)} keywords from JD not found — tailor your resume to this role")
        elif raw > 0.75:
            feedback.append("Strong keyword match with the job description")

        match_pct = int(raw * 100)
        bd.append(("JD keywords matched", len(matched), len(jd_keywords),
                   f"{match_pct}% match — {len(matched)} of {len(jd_keywords)} keywords found"))
        bd.append(("Critical keywords",
                   len([k for k, is_c in missing if is_c]),
                   0,   # informational
                   f"{len(critical_missing)} critical keywords missing" if critical_missing else "All critical keywords present"))
        bd.append(("Placement quality",
                   sum(1 for _, _, b in matched if b > 0),
                   len(matched),
                   "Keywords found in high-value sections (summary/experience)"))

    else:
        # ── MODE 2: No JD — score general professional vocabulary ──
        text_lower = text.lower()

        # General professional / technical vocabulary signals
        professional_vocab = [
            "developed", "implemented", "managed", "led", "built", "designed",
            "analysed", "analyzed", "optimized", "delivered", "achieved",
            "collaborated", "coordinated", "created", "launched", "deployed",
            "results", "impact", "performance", "growth", "revenue", "team",
        ]
        # STANDARD ATS ALGORITHM (NO JD PROVIDED)
        # We do not penalize the user. We will zero out this component's weight later
        # and redistribute it to formatting/experience so the ATS score is 100% accurate to the resume itself.
        raw = 0.0
        feedback.append("Note: Paste a Job Description to unlock keyword match analysis (Optional).")
        
        bd.append(("Keyword Analysis", 0, 0, "Paste a job description for keyword scoring"))

    return ComponentResult(
        "keyword_coverage", w, raw, raw * w, bd, feedback,
    ), matched, missing


# ─────────────────────────────────────────────
#  MAIN ANALYSER
# ─────────────────────────────────────────────

def analyze_resume(resume_text: str, job_description: str = "") -> ATSResult:
    """
    Master function. Call this with raw resume text.
    Returns a fully explainable ATSResult — no fake values.

    Parameters
    ----------
    resume_text     : Plain text extracted from the resume (PDF/DOCX parsed upstream)
    job_description : Optional. Paste the target job posting for keyword matching.

    Returns
    -------
    ATSResult with total score, per-component breakdown, and actionable feedback.
    """
    if not resume_text or len(resume_text.strip()) < 50:
        raise ValueError("Resume text is too short to analyze. Minimum 50 characters required.")

    components = {}
    parsing_warnings = []

    # Run all scorers
    components["contact_info"]          = score_contact_info(resume_text)
    components["professional_summary"]  = score_professional_summary(resume_text)
    components["skills_section"]        = score_skills_section(resume_text)
    components["experience_section"]    = score_experience_section(resume_text)
    components["education_section"]     = score_education(resume_text)
    components["projects_section"]      = score_projects(resume_text)
    components["certifications"]        = score_certifications(resume_text)
    components["ats_formatting"]        = score_ats_formatting(resume_text)

    # Keyword coverage returns extra data
    kw_result, kw_matched, kw_missing = score_keyword_coverage(resume_text, job_description)
    
    if not job_description.strip():
        # Standard ATS logic: If no JD is provided, we zero out the keyword requirement
        # and redistribute the 20% weight strictly to Formatting and Experience 
        # so the resume is judged purely on its own ATS merits.
        kw_result.weight = 0
        kw_result.weighted = 0
        
        components["experience_section"].weight += 10
        components["experience_section"].weighted = components["experience_section"].raw_score * components["experience_section"].weight
        
        components["ats_formatting"].weight += 10
        components["ats_formatting"].weighted = components["ats_formatting"].raw_score * components["ats_formatting"].weight

    components["keyword_coverage"] = kw_result

    # Total score
    total_float = sum(c.weighted for c in components.values())
    total_score = max(0, min(100, round(total_float)))

    # Grade
    grade, grade_label = _grade(total_score)

    # Collect all feedback, prioritise by component weight
    all_feedback = []
    for name, result in sorted(components.items(), key=lambda x: -x[1].weight):
        for f in result.feedback:
            all_feedback.append((result.weight, f))

    top_issues = [f for _, f in sorted(all_feedback, key=lambda x: -x[0])[:3]]

    # Parsing warnings (structural issues)
    if len(resume_text) < 300:
        parsing_warnings.append("Resume text is very short — ensure full text was extracted")
    if not any(re.search(p, resume_text.lower(), re.MULTILINE) for p in SECTION_PATTERNS.values()):
        parsing_warnings.append("No standard section headers detected — may be a parsing issue")

    logging.info("ATS_ENGINE_COMPLETED")

    return ATSResult(
        total_score    = total_score,
        grade          = grade,
        grade_label    = grade_label,
        components     = components,
        keyword_matches= [kw for kw, _, _ in kw_matched],
        keyword_missing= [kw for kw, _ in kw_missing],
        top_issues     = top_issues,
        parsing_warnings = parsing_warnings,
    )


# ─────────────────────────────────────────────
#  FLASK API INTEGRATION
# ─────────────────────────────────────────────

def build_api_response(result: ATSResult) -> dict:
    """
    Converts ATSResult into a clean JSON-serialisable dict
    for your existing Flask /api/ats/analyze endpoint.
    """
    return {
        "ats_score": result.total_score,
        "grade": result.grade,
        "grade_label": result.grade_label,
        "components": {
            name: {
                "label": name.replace("_", " ").title(),
                "weight": comp.weight,
                "score_raw": round(comp.raw_score, 3),
                "score_weighted": round(comp.weighted, 2),
                "percentage": int(comp.raw_score * 100),
                "breakdown": [
                    {
                        "signal": b[0],
                        "earned": b[1],
                        "max": b[2],
                        "note": b[3],
                    }
                    for b in comp.breakdown
                ],
                "feedback": comp.feedback,
            }
            for name, comp in result.components.items()
        },
        "keyword_matches": result.keyword_matches[:30],   # top 30
        "keyword_missing": result.keyword_missing[:20],   # top 20 missing
        "top_issues": result.top_issues,
        "parsing_warnings": result.parsing_warnings,
        "engine": "algorithmic_v1",      # never says 'gemini' or 'ai'
        "score_is_deterministic": True,
    }
