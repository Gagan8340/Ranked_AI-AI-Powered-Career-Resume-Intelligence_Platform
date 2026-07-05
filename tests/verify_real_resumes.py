import json
from config import get_db_connection
from utils.ats_engine import evaluate_resume

print("=== FINAL ATS VERIFICATION TESTS ===\n")

# 1. Answer: Why did Strong Resume score 96 instead of 100?
strong_resume = """Jane Doe
jane.doe@email.com
(555) 987-6543
linkedin.com/in/janedoe
github.com/janedoe

SUMMARY
Highly skilled Senior Software Engineer with 6+ years of experience in designing, developing, and optimizing highly scalable cloud applications. Proven track record of improving system performance and leading agile teams.

SKILLS
Languages: Python, JavaScript, Java, Go, TypeScript
Frameworks: React, Django, Node.js, Next.js
Tools & Cloud: AWS, Docker, Kubernetes, CI/CD, Git, MySQL, Redis

EXPERIENCE
Senior Software Engineer
Tech Innovations Inc.
- Architected and developed a distributed microservices platform using Python, Django, and AWS, serving over 100,000 active users.
- Optimized database queries in PostgreSQL, reducing average response time by 45%.
- Managed a team of 4 junior developers, increasing sprint velocity by 20% over 6 months.
- Integrated automated CI/CD pipelines using GitHub Actions and Docker, reducing deployment time from hours to 15 minutes.
- Spearheaded the migration of legacy monolith to Kubernetes, resulting in a 30% infrastructure cost savings ($50,000 annually).

Software Engineer
DataCorp
- Engineered data processing pipelines in Python and Pandas to analyze 50TB of daily user data.
- Resolved 50+ critical production bugs, achieving a 99.9% uptime SLA.
- Developed RESTful APIs for mobile clients using Express and Node.js.

PROJECTS
Real-Time Analytics Dashboard
- Built a real-time analytics dashboard using React, WebSockets, and Redis.
- Handled 10,000 concurrent websocket connections with zero downtime.
- Live deployment at https://analytics.live

EDUCATION
Master of Science in Computer Science
State University, 2018
GPA: 3.9/4.0"""

result_strong = evaluate_resume(strong_resume)
print(f"Strong Resume Overall Score: {result_strong['overall_score']}")
print(f"Breakdown: {json.dumps(result_strong['breakdown'], indent=2)}")
print(f"Improvements: {result_strong['recommendations']}")
print("-" * 50)

# 2. Dynamic Score Changes Tests
print("\n--- DYNAMIC SCORE VERIFICATION ---\n")

base_resume = """John Doe
john@email.com

EXPERIENCE
- Did some stuff.
- Worked on a project."""

# 2A. Formatting changes when formatting changes
form_bad = evaluate_resume("John Doe\nNo formatting here.")
form_good = evaluate_resume("John Doe\njohn@example.com\n555-1234\ngithub.com/johndoe\n\nEXPERIENCE\n- Bullet 1\n- Bullet 2\n- Bullet 3\n- Bullet 4\n- Bullet 5")
print(f"Formatting Test: Bad={form_bad['breakdown']['formatting']['score']} -> Good={form_good['breakdown']['formatting']['score']}")

# 2B. Readability changes
read_bad = evaluate_resume("EXPERIENCE\n" + ("This is a very long block of text that just goes on and on without any bullet points to break it up and makes it incredibly difficult to read. " * 10))
read_good = evaluate_resume("EXPERIENCE\n- Short concise bullet point.\n- Another short bullet point.\n- Quantifiable results shown here.")
print(f"Readability Test: Bad={read_bad['breakdown']['readability']['score']} -> Good={read_good['breakdown']['readability']['score']}")

# 2C. Project Quality changes
proj_bad = evaluate_resume("PROJECTS\nCool App")
proj_good = evaluate_resume("PROJECTS\nCool App\n- Built with Python, React, and AWS.\n- Handled 10,000 requests.\n- Code at github.com/johndoe")
print(f"Project Test: Bad={proj_bad['breakdown']['project']['score']} -> Good={proj_good['breakdown']['project']['score']}")

# 2D. Experience Quality changes
exp_bad = evaluate_resume("EXPERIENCE\n- worked on website\n- helped team")
exp_good = evaluate_resume("EXPERIENCE\n- Developed a React website used by 10,000 users.\n- Optimized SQL queries reducing latency by 45%.")
print(f"Experience Test: Bad={exp_bad['breakdown']['experience']['score']} -> Good={exp_good['breakdown']['experience']['score']}")

print("-" * 50)
print("\n--- 5 REAL RESUME REPORTS ---\n")

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT resume_id, resume_text FROM resumes WHERE resume_text IS NOT NULL AND resume_text != '' LIMIT 5")
resumes = cursor.fetchall()

for i, row in enumerate(resumes):
    res_text = row['resume_text']
    result = evaluate_resume(res_text)
    
    print(f"Resume {i+1} (ID: {row['resume_id']})")
    print(f"Overall Score: {result['overall_score']}")
    print("Breakdown:")
    for k, v in result['breakdown'].items():
        print(f"  - {k.title()}: {v['score']}")
    print(f"Missing Sections: {result['missing_sections']}")
    print(f"Weak Areas: {result['weak_areas']}")
    print(f"Improvement Suggestions (Limit 3):")
    for r in result['recommendations'][:3]:
        print(f"  * {r}")
    print("\n" + "=" * 50 + "\n")
