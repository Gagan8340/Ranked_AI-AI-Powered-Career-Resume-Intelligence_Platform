from config import get_db_connection
from utils.profile_strength import calculate_profile_strength

user_id = 1

def print_result():
    data = calculate_profile_strength(user_id)
    print(f"Total Score: {data['total_score']}%")
    print(f"Missing Items: {data['missing_items']}")
    print("Categories Breakdown:")
    for cat, items in data['categories'].items():
        print(f"  {cat}:")
        for k, v in items.items():
            print(f"    {k}: {v}")
    print("-" * 40)

print("--- INITIAL STATE ---")
print_result()

# 1. Update GitHub
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("UPDATE builder_profiles SET github = 'https://github.com/test' WHERE user_id = %s", (user_id,))
conn.commit()
print("--- ADDED GITHUB ---")
print_result()

# 2. Add Project
cursor.execute("INSERT INTO user_projects (user_id, project_name) VALUES (%s, 'Test Proj')", (user_id,))
conn.commit()
print("--- ADDED PROJECT ---")
print_result()

# 3. Add Certification
cursor.execute("INSERT INTO certifications (user_id, name) VALUES (%s, 'Test Cert')", (user_id,))
conn.commit()
print("--- ADDED CERTIFICATION ---")
print_result()

# Teardown
cursor.execute("UPDATE builder_profiles SET github = '' WHERE user_id = %s", (user_id,))
cursor.execute("DELETE FROM user_projects WHERE project_name = 'Test Proj'")
cursor.execute("DELETE FROM certifications WHERE name = 'Test Cert'")
conn.commit()
conn.close()
