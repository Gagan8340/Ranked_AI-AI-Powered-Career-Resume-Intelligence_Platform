import glob

files = glob.glob('templates/*.html')

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Vertically center the text on the left side instead of sticking it to the bottom
    content = content.replace('justify-content: flex-end;', 'justify-content: center;')
    
    if content != original:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')
