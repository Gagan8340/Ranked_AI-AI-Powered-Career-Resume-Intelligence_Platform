import os
import re

directories = ['d:\\smartcampus\\smartcampus-ai\\routes', 'd:\\smartcampus\\smartcampus-ai\\services', 'd:\\smartcampus\\smartcampus-ai\\utils', 'd:\\smartcampus\\smartcampus-ai']

with open('data/queries_out.txt', 'w', encoding='utf-8') as out:
    for d in directories:
        for root, dirs, files in os.walk(d):
            if 'venv' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.endswith('.py') and file != 'audit_queries.py':
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'cursor.execute' in line or 'SELECT ' in line.upper() or 'INSERT INTO' in line.upper() or 'UPDATE ' in line.upper() or 'DELETE FROM' in line.upper():
                            if 'SELECT COUNT' not in line.upper():
                                out.write(f"{filepath}:{i+1}: {line.strip()}\n")
