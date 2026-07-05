import json
from utils.ats_engine import evaluate_resume

test_cases = [
    {
        "name": "A. Blank resume",
        "content": "   "
    },
    {
        "name": "B. Education-only resume",
        "content": """John Doe
john@example.com
555-1234

EDUCATION
University of Technology
BS in Computer Science
Graduated 2024
GPA 3.8"""
    },
    {
        "name": "C. Student resume with projects",
        "content": """John Doe
john@example.com
555-1234
github.com/johndoe

EDUCATION
University of Technology
BS in Computer Science

SKILLS
Python, JavaScript, React, SQL, HTML, CSS

PROJECTS
Weather App
- Built a weather application using Python and React.
- Used external APIs to fetch data.
- Handled 500 requests per day.
- Deployed on Vercel."""
    },
    {
        "name": "D. Strong ATS resume",
        "content": """Jane Doe
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
    }
]

print("=== ATS SCORE CHECKER VERIFICATION ===\n")
for case in test_cases:
    result = evaluate_resume(case["content"])
    print(f"--- {case['name']} ---")
    print(f"Overall Score: {result['overall_score']}")
    for k, v in result['breakdown'].items():
        print(f"  {k.title():<15}: {v['score']}")
    print("  Missing Sections:", result.get('missing_sections', []))
    print("  Weak Areas:", result.get('weak_areas', []))
    print("  Improvements:", len(result.get('recommendations', [])))
    print()
