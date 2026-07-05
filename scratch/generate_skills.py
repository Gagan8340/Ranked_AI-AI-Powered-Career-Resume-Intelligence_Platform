import os, json, time
from dotenv import load_dotenv
from google import genai

load_dotenv('d:/smartcampus/smartcampus-ai/.env')

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

prompt = """
Return a comprehensive JSON array of exactly 500 major professional skills. 
Include a mix of:
- Hard/Technical Skills (e.g., Python, JavaScript, React, Machine Learning, AWS, Docker, SQL)
- Domain Skills (e.g., Project Management, Agile, SEO, Digital Marketing, Data Analysis)
- Soft Skills (e.g., Leadership, Communication, Problem Solving, Teamwork)
Make sure they are properly capitalized and formatted as strings. 
Do not include any markdown, just the raw JSON array.
["Python", "Project Management", "Leadership", ...]
"""

max_retries = 3
for attempt in range(max_retries):
    try:
        print(f"Attempt {attempt+1}...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        skills = json.loads(text.strip())
        print(f"Successfully generated {len(skills)} skills.")
        
        # Ensure directory exists
        os.makedirs('d:/smartcampus/smartcampus-ai/static/data', exist_ok=True)
        
        # Save to file
        with open('d:/smartcampus/smartcampus-ai/static/data/skills.json', 'w') as f:
            json.dump(sorted(list(set(skills))), f, indent=4)
        
        print("Saved to static/data/skills.json")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
