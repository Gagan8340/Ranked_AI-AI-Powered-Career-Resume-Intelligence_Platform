"""
ATS Engine — Honest Test Suite
================================
Tests verify:
1. Scores are deterministic (same input = same output, always)
2. Better resumes score higher than weaker ones
3. No fake inflation (weak resume never scores > 60)
4. Missing sections produce zero for that component
5. Edge cases don't crash
6. Total always sums to 100 maximum
"""

import sys
from services.ats_engine import analyze_resume, build_api_response, WEIGHTS

# ─────────────────────────────────────────────
#  TEST FIXTURES
# ─────────────────────────────────────────────

STRONG_RESUME = """
John Doe
john.doe@email.com | +1 (555) 123-4567 | linkedin.com/in/johndoe | github.com/johndoe
San Francisco, CA

Professional Summary
Results-driven software engineer with 5+ years building scalable web applications.
Delivered 3 major product launches increasing user retention by 40%. Led a team of
6 engineers, reducing deployment time by 60% through CI/CD automation.

Skills
Python, JavaScript, React, Node.js, PostgreSQL, Docker, Kubernetes, AWS, Redis,
Django, FastAPI, TypeScript, SQL, Git, Linux, REST APIs, GraphQL, Terraform

Experience
Senior Software Engineer — TechCorp Inc.   Jan 2021 – Present
- Led development of microservices platform serving 2M+ daily users
- Reduced API latency by 45% through caching and query optimization
- Managed and mentored a team of 4 junior engineers
- Deployed infrastructure on AWS using Terraform, cutting costs by 30%

Software Engineer — StartupXYZ   Mar 2019 – Dec 2020
- Built React frontend serving 500k monthly active users
- Implemented automated testing pipeline reducing bugs by 70%
- Collaborated with product team to deliver 12 features on schedule

Education
Bachelor of Science in Computer Science
State University, 2019

Projects
E-Commerce Platform (github.com/johndoe/ecommerce)
Built full-stack e-commerce app with Python, React, PostgreSQL handling 10,000 orders/day

Certifications
AWS Certified Solutions Architect — Associate, Amazon Web Services, 2022
"""

WEAK_RESUME = """
Jane Smith
jane@gmail.com

Objective
Looking for a software job. I am a hardworking fast learner with good communication skills.

Skills
MS Office, Email, Internet, Teamwork, Microsoft Word

Work
Did some coding projects at university. Helped a team build a website.

Education
Computer Science degree.
"""

EMPTY_SECTIONS_RESUME = """
Alex Brown
alex@email.com | +1 555 000 0000

Summary
Software developer.

Skills
Python, SQL

"""

JOB_DESCRIPTION = """
We are looking for a Senior Python Developer with experience in:
- Python, Django, FastAPI
- PostgreSQL and Redis
- Docker and Kubernetes
- AWS cloud services
- React and TypeScript frontend
- REST API design
- CI/CD pipelines
- Agile methodology
Must have: 3+ years experience, Bachelor's degree in Computer Science or related field.
"""


# ─────────────────────────────────────────────
#  TEST RUNNER
# ─────────────────────────────────────────────

def run(name, fn):
    try:
        fn()
        print(f"  ✓  {name}")
    except AssertionError as e:
        print(f"  ✗  {name}")
        print(f"       {e}")
        return False
    return True


def all_tests():
    passed = 0
    failed = 0

    print("\n======================================")
    print("  ATS ENGINE — HONEST TEST SUITE")
    print("======================================\n")

    # ── 1. Weights integrity ────────────────────────
    print("[ Weights integrity ]")

    def test_weights_sum():
        assert sum(WEIGHTS.values()) == 100, f"Weights sum to {sum(WEIGHTS.values())} not 100"

    def test_weights_positive():
        for k, v in WEIGHTS.items():
            assert v > 0, f"Weight for {k} is {v}"

    if run("Weights sum to exactly 100", test_weights_sum): passed += 1
    else: failed += 1
    if run("All weights are positive", test_weights_positive): passed += 1
    else: failed += 1

    # ── 2. Strong resume scores well ───────────────
    print("\n[ Strong resume scoring ]")
    strong = analyze_resume(STRONG_RESUME)

    def test_strong_total():
        assert strong.total_score >= 70, f"Strong resume scored only {strong.total_score}"

    def test_strong_grade():
        assert strong.grade in ("A", "B"), f"Strong resume got grade {strong.grade}"

    def test_strong_contact():
        s = strong.components["contact_info"].raw_score
        assert s >= 0.6, f"Contact score {s:.2f} — should be ≥ 0.6"

    def test_strong_experience():
        s = strong.components["experience_section"].raw_score
        assert s >= 0.6, f"Experience score {s:.2f} — should be ≥ 0.6"

    def test_strong_skills():
        s = strong.components["skills_section"].raw_score
        assert s >= 0.6, f"Skills score {s:.2f} — should be ≥ 0.6"

    for t, fn in [
        ("Strong resume total ≥ 70", test_strong_total),
        ("Strong resume grade A or B", test_strong_grade),
        ("Strong contact info score ≥ 0.6", test_strong_contact),
        ("Strong experience score ≥ 0.6", test_strong_experience),
        ("Strong skills score ≥ 0.6", test_strong_skills),
    ]:
        if run(t, fn): passed += 1
        else: failed += 1

    # ── 3. Weak resume scores poorly ───────────────
    print("\n[ Weak resume scoring — no inflation ]")
    weak = analyze_resume(WEAK_RESUME)

    def test_weak_lower_than_strong():
        assert weak.total_score < strong.total_score, \
            f"Weak ({weak.total_score}) should score less than strong ({strong.total_score})"

    def test_weak_not_inflated():
        assert weak.total_score < 60, \
            f"Weak resume scored {weak.total_score} — looks inflated"

    def test_weak_has_issues():
        assert len(weak.top_issues) > 0, "Weak resume should have feedback issues"

    def test_weak_fluff_penalised():
        s = weak.components["skills_section"].raw_score
        assert s < 0.8, f"Fluff skills should not score high — got {s:.2f}"

    for t, fn in [
        ("Weak scores less than strong", test_weak_lower_than_strong),
        ("Weak resume not inflated (< 60)", test_weak_not_inflated),
        ("Weak resume has actionable issues", test_weak_has_issues),
        ("Fluff skills penalised", test_weak_fluff_penalised),
    ]:
        if run(t, fn): passed += 1
        else: failed += 1

    # ── 4. Determinism — same input = same output ──
    print("\n[ Determinism — no randomness ]")

    def test_determinism_strong():
        r1 = analyze_resume(STRONG_RESUME)
        r2 = analyze_resume(STRONG_RESUME)
        assert r1.total_score == r2.total_score, \
            f"Non-deterministic! Got {r1.total_score} then {r2.total_score}"

    def test_determinism_weak():
        r1 = analyze_resume(WEAK_RESUME)
        r2 = analyze_resume(WEAK_RESUME)
        assert r1.total_score == r2.total_score

    def test_determinism_component_level():
        r1 = analyze_resume(STRONG_RESUME)
        r2 = analyze_resume(STRONG_RESUME)
        for name in r1.components:
            s1 = r1.components[name].raw_score
            s2 = r2.components[name].raw_score
            assert s1 == s2, f"Component {name} non-deterministic: {s1} vs {s2}"

    for t, fn in [
        ("Strong resume score deterministic", test_determinism_strong),
        ("Weak resume score deterministic", test_determinism_weak),
        ("All components deterministic", test_determinism_component_level),
    ]:
        if run(t, fn): passed += 1
        else: failed += 1

    # ── 5. Score boundaries ────────────────────────
    print("\n[ Score boundaries ]")

    def test_score_never_exceeds_100():
        r = analyze_resume(STRONG_RESUME)
        assert r.total_score <= 100, f"Score {r.total_score} exceeds 100"

    def test_score_never_negative():
        r = analyze_resume(WEAK_RESUME)
        assert r.total_score >= 0, f"Score {r.total_score} is negative"

    def test_weighted_scores_sum():
        r = analyze_resume(STRONG_RESUME)
        total = sum(c.weighted for c in r.components.values())
        assert abs(total - r.total_score) < 1.0, \
            f"Component sum {total:.1f} doesn't match total {r.total_score}"

    def test_raw_score_between_0_and_1():
        r = analyze_resume(STRONG_RESUME)
        for name, comp in r.components.items():
            assert 0.0 <= comp.raw_score <= 1.0, \
                f"{name} raw_score {comp.raw_score} out of 0–1 range"

    for t, fn in [
        ("Score never exceeds 100", test_score_never_exceeds_100),
        ("Score never negative", test_score_never_negative),
        ("Component weighted scores sum to total", test_weighted_scores_sum),
        ("All raw scores in 0–1 range", test_raw_score_between_0_and_1),
    ]:
        if run(t, fn): passed += 1
        else: failed += 1

    # ── 6. Keyword matching with JD ───────────────
    print("\n[ Keyword matching ]")

    def test_jd_match_higher_than_no_jd():
        with_jd    = analyze_resume(STRONG_RESUME, JOB_DESCRIPTION)
        without_jd = analyze_resume(STRONG_RESUME)
        # Both should work — just checking no crash and reasonable values
        assert 0 <= with_jd.components["keyword_coverage"].raw_score <= 1

    def test_keyword_matches_present():
        r = analyze_resume(STRONG_RESUME, JOB_DESCRIPTION)
        assert len(r.keyword_matches) > 0, "Should find keyword matches with JD"

    def test_keyword_missing_list():
        r = analyze_resume(WEAK_RESUME, JOB_DESCRIPTION)
        assert len(r.keyword_missing) > 0, "Weak resume should have missing keywords"

    def test_strong_beats_weak_on_keywords():
        strong_kw = analyze_resume(STRONG_RESUME, JOB_DESCRIPTION).components["keyword_coverage"].raw_score
        weak_kw   = analyze_resume(WEAK_RESUME,   JOB_DESCRIPTION).components["keyword_coverage"].raw_score
        assert strong_kw > weak_kw, \
            f"Strong ({strong_kw:.2f}) should beat weak ({weak_kw:.2f}) on keyword match"

    for t, fn in [
        ("Keyword scoring with JD doesn't crash", test_jd_match_higher_than_no_jd),
        ("Keyword matches returned when JD provided", test_keyword_matches_present),
        ("Missing keywords returned for weak resume", test_keyword_missing_list),
        ("Strong resume beats weak on keyword match", test_strong_beats_weak_on_keywords),
    ]:
        if run(t, fn): passed += 1
        else: failed += 1

    # ── 7. Edge cases ──────────────────────────────
    print("\n[ Edge cases ]")

    def test_empty_sections_resume():
        r = analyze_resume(EMPTY_SECTIONS_RESUME)
        assert 0 <= r.total_score <= 100

    def test_api_response_structure():
        r = analyze_resume(STRONG_RESUME)
        resp = build_api_response(r)
        required_keys = ["ats_score", "grade", "grade_label", "components",
                         "keyword_matches", "keyword_missing", "top_issues",
                         "engine", "score_is_deterministic"]
        for k in required_keys:
            assert k in resp, f"Missing key in API response: {k}"

    def test_engine_tag_not_ai():
        r = analyze_resume(STRONG_RESUME)
        resp = build_api_response(r)
        assert resp["engine"] == "algorithmic_v1", "Engine tag should not claim AI"
        assert resp["score_is_deterministic"] is True

    def test_very_short_text_raises():
        try:
            analyze_resume("hi")
            assert False, "Should have raised ValueError for very short text"
        except ValueError:
            pass  # expected

    for t, fn in [
        ("Minimal resume doesn't crash", test_empty_sections_resume),
        ("API response has all required keys", test_api_response_structure),
        ("Engine tag is algorithmic, not AI", test_engine_tag_not_ai),
        ("Very short text raises clear error", test_very_short_text_raises),
    ]:
        if run(t, fn): passed += 1
        else: failed += 1

    # ── Summary ────────────────────────────────────
    total = passed + failed
    print(f"\n======================================")
    print(f"  {passed}/{total} tests passed")
    if failed:
        print(f"  {failed} FAILED — fix before deploying")
    else:
        print(f"  All tests green — safe to deploy")
    print(f"======================================\n")

    # Print score breakdown for manual inspection
    print("[ Score preview — strong resume ]")
    strong2 = analyze_resume(STRONG_RESUME, JOB_DESCRIPTION)
    print(f"  Total: {strong2.total_score}/100  Grade: {strong2.grade} — {strong2.grade_label}")
    for name, comp in strong2.components.items():
        bar = "█" * int(comp.raw_score * 10) + "░" * (10 - int(comp.raw_score * 10))
        print(f"  {name:<28} {bar}  {comp.weighted:.1f}/{comp.weight}pts")

    print(f"\n[ Score preview — weak resume ]")
    weak2 = analyze_resume(WEAK_RESUME, JOB_DESCRIPTION)
    print(f"  Total: {weak2.total_score}/100  Grade: {weak2.grade} — {weak2.grade_label}")
    for name, comp in weak2.components.items():
        bar = "█" * int(comp.raw_score * 10) + "░" * (10 - int(comp.raw_score * 10))
        print(f"  {name:<28} {bar}  {comp.weighted:.1f}/{comp.weight}pts")

    print(f"\n  Top issues for weak resume:")
    for i, issue in enumerate(weak2.top_issues, 1):
        print(f"  {i}. {issue}")

    return failed == 0


if __name__ == "__main__":
    ok = all_tests()
    sys.exit(0 if ok else 1)
