import glob
import re

files = glob.glob('templates/*login.html') + glob.glob('templates/*register.html')

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Body adjustments for full screen
    content = re.sub(r'body\s*\{([^\}]*)\}','body { margin: 0; padding: 0; min-height: 100vh; background: linear-gradient(-45deg, #09090b, #18181b, #121214, #0a0a0c); background-size: 400% 400%; animation: gradientShift 15s ease infinite; display: flex; align-items: stretch; justify-content: stretch; font-family: \'Inter\', sans-serif; }', content)
    
    # Wrapper full screen
    content = re.sub(r'\.wrapper\s*\{[^\}]*\}', '.wrapper { width: 100%; min-height: 100vh; display: flex; flex-direction: row; border-radius: 0; margin: 0; background: transparent; border: none; box-shadow: none; animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; overflow-y: auto; }', content)
    
    # Left Side
    content = re.sub(r'\.left\s*\{[^\}]*\}', '.left { flex: 0 0 45%; position: relative; display: flex; flex-direction: column; justify-content: center; padding: 6vw; background: rgba(10, 13, 26, 0.3); border-right: 1px solid rgba(255, 255, 255, 0.05); }', content)
    
    # Right Side
    content = re.sub(r'\.right\s*\{[^\}]*\}', '.right { flex: 1; display: flex; align-items: center; justify-content: center; padding: 4vw; background: transparent; position: relative; }', content)
    
    # Left Overlay with subtle glowing orbs
    content = re.sub(r'\.left-overlay\s*\{[^\}]*\}', '.left-overlay { position: absolute; inset: 0; background: radial-gradient(circle at 20% 30%, rgba(139,109,253,0.1), transparent 60%), radial-gradient(circle at 80% 80%, rgba(99,102,241,0.08), transparent 60%); pointer-events: none; }', content)

    if content != original:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')
