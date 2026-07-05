import glob
import re

files = glob.glob('templates/*.html')
files += glob.glob('static/css/*.css')

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. Remove canvas element
    content = content.replace('<canvas id="net"></canvas>', '')
    
    # 2. Update gradient to remove bright purple phase
    content = content.replace('linear-gradient(-45deg, #09090b, #18181b, #2e1065, #1c192b)', 'linear-gradient(-45deg, #09090b, #18181b, #121214, #0a0a0c)')
    content = content.replace('linear-gradient(-45deg, var(--bg-primary), var(--bg-secondary), #2e1065, #1c192b)', 'linear-gradient(-45deg, var(--bg-primary), var(--bg-secondary), #121214, #0a0a0c)')
    
    # 3. Remove JS block for the canvas animation
    # The canvas JS block looks like:
    # var canvas = document.getElementById('net'); ... draw();
    content = re.sub(r'var\s+canvas\s*=\s*document\.getElementById\(\'net\'\);.*?draw\(\);', '', content, flags=re.DOTALL)
    
    # Clean up any empty anonymous function blocks left behind
    content = re.sub(r'\(function\s*\(\)\s*\{\s*\}\)\(\);', '', content)
    
    if content != original:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')
