import re

with open('templates/settings.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Update CSS for smooth transition
old_css = '''.accordion-content {
    transition: all 0.3s ease-in-out;
    overflow: hidden;
    max-height: 2000px;
    opacity: 1;
}'''

new_css = '''.accordion-content {
    transition: max-height 0.3s ease-in-out, opacity 0.3s ease-in-out, margin-top 0.3s ease-in-out;
    overflow: hidden;
    opacity: 1;
}'''
content = content.replace(old_css, new_css)

content = content.replace('max-height: 0;', 'max-height: 0 !important;')

# Replace old JS function
old_js = '''function toggleAccordion(header) {
    const content = header.nextElementSibling;
    const icon = header.querySelector('.accordion-icon');
    content.classList.toggle('collapsed');
    icon.classList.toggle('collapsed');
    
    if (content.classList.contains('collapsed')) {
        header.style.marginBottom = "0";
    } else {
        header.style.marginBottom = "var(--space-4)";
    }
}'''

new_js = '''function toggleAccordion(header) {
    const content = header.nextElementSibling;
    const icon = header.querySelector('.accordion-icon');
    const isCollapsed = content.classList.contains('collapsed');
    
    if (isCollapsed) {
        // OPENING
        content.classList.remove('collapsed');
        icon.classList.remove('collapsed');
        header.style.marginBottom = "var(--space-4)";
        
        // Use scrollHeight for smooth transition to exact height
        content.style.maxHeight = content.scrollHeight + "px";
        
        // Clear fixed height after animation completes so content can grow
        setTimeout(() => {
            if (!content.classList.contains('collapsed')) {
                content.style.maxHeight = 'none';
            }
        }, 300);
    } else {
        // CLOSING
        // Set fixed height first so transition knows where to start from 'none'
        content.style.maxHeight = content.scrollHeight + "px";
        
        // Force browser repaint to acknowledge the fixed height before changing it to 0
        void content.offsetWidth;
        
        content.classList.add('collapsed');
        icon.classList.add('collapsed');
        header.style.marginBottom = "0";
        content.style.maxHeight = "0px";
    }
}'''

if old_js in content:
    content = content.replace(old_js, new_js)
    with open('templates/settings.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed accordion harshness perfectly!")
else:
    print("Could not find the exact JS. Check for partial matches.")
