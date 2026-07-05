import os
import re

base_dir = "d:/smartcampus/smartcampus-ai"

css_append = """
/* UI-7 Premium Enhancements */
.fade-up { opacity: 0; transform: translateY(16px) scale(0.98); transition: opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1), transform 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-up.visible { opacity: 1; transform: translateY(0) scale(1); }

/* Stagger system */
.stagger-1 { transition-delay: 40ms; }
.stagger-2 { transition-delay: 80ms; }
.stagger-3 { transition-delay: 120ms; }
.stagger-4 { transition-delay: 160ms; }

/* Global Transitions & Easing */
:root {
  --t-fast: 120ms;
  --t-normal: 180ms;
  --t-smooth: 280ms;
  --t-large: 420ms;
  --ease-premium: cubic-bezier(0.4, 0, 0.2, 1);
}
* { transition-timing-function: var(--ease-premium); }

/* Card & Button Hover System */
.widget-card, .card, .action-card, .panel { 
    transition: transform var(--t-smooth), box-shadow var(--t-smooth), border-color var(--t-smooth), background var(--t-smooth); 
}
.widget-card:hover, .card:hover, .action-card:hover, .panel:hover { 
    transform: translateY(-4px); 
    box-shadow: 0 24px 48px -12px rgba(124,58,237,0.15), 0 0 0 1px rgba(124,58,237,0.2) inset; 
    border-color: rgba(124,58,237,0.4); 
}

.btn-primary, .btn-secondary, .btn-ghost, .chip {
    transition: transform var(--t-normal), box-shadow var(--t-normal), filter var(--t-fast);
}
.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 24px -8px rgba(124,58,237,0.6);
    filter: brightness(1.1);
}
.chip:hover {
    transform: scale(1.05);
    box-shadow: 0 0 12px rgba(124,58,237,0.3);
}

/* Skeleton & Loading States */
.skeleton {
    background: linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.02) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s var(--ease-premium) infinite;
    border-radius: var(--radius-sm);
    min-height: 24px;
}
@keyframes shimmer { 
    0% { background-position: -200% 0; } 
    100% { background-position: 200% 0; } 
}

/* Intelligent Empty State */
.empty-state, .premium-empty {
    text-align: center;
    padding: var(--space-8) var(--space-4);
    color: var(--text-muted);
    background: radial-gradient(circle at center, rgba(255,255,255,0.03) 0%, transparent 70%);
    border-radius: var(--radius-md);
    font-weight: 400;
    font-size: var(--text-md);
    letter-spacing: -0.01em;
    border: 1px dashed rgba(255,255,255,0.08);
    transition: border-color var(--t-smooth);
}
.empty-state:hover { border-color: rgba(255,255,255,0.15); }

/* Sidebar Premium Hover */
.nav-item { transition: background var(--t-normal), color var(--t-normal), transform var(--t-normal); }
.nav-item:hover { transform: translateX(4px); background: rgba(124,58,237,0.08); }

/* Responsive Tweaks */
@media (max-width: 768px) {
    .sidebar { transition: transform var(--t-smooth); }
    .widget-card, .card { margin-bottom: var(--space-4); width: 100%; overflow: hidden; }
    .topbar { position: sticky; top: 0; backdrop-filter: blur(16px); z-index: 100; }
}
"""

js_append = """
// UI-7 Premium Animations & Intersection Observer
document.addEventListener('DOMContentLoaded', () => {
    const observerOptions = { threshold: 0.05, rootMargin: "0px 0px -20px 0px" };
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, i) => {
            if(entry.isIntersecting) {
                // Apply stagger dynamically based on index if multiple appear at once
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, i * 50);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Attach to all cards and major sections
    const elements = document.querySelectorAll('.widget-card, .card, .panel, .stat-card, section, .focus-item');
    elements.forEach(el => {
        el.classList.add('fade-up');
        observer.observe(el);
    });
});
"""

css_path = os.path.join(base_dir, "static/css/main.css")
with open(css_path, "a", encoding="utf-8") as f:
    f.write(css_append)

js_path = os.path.join(base_dir, "static/js/main.js")
if os.path.exists(js_path):
    with open(js_path, "a", encoding="utf-8") as f:
        f.write(js_append)
else:
    # fallback to base.html if main.js doesn't exist
    pass

# Update HTML Empty States
empty_states_map = [
    (r"No data found", "Nothing due right now. Nice."),
    (r"Nothing here", "Your study system is calm today."),
    (r"No records", "No academic risks detected."),
    (r"Empty", "Your AI copilot is ready.")
]

templates_dir = os.path.join(base_dir, "templates")
if os.path.exists(templates_dir):
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                original_content = content
                for old, new in empty_states_map:
                    content = re.sub(old, new, content, flags=re.IGNORECASE)
                
                # specific updates for skeleton loaders in standard places
                content = content.replace('class="loader"', 'class="skeleton"')
                content = content.replace('class="spinner"', 'class="skeleton"')

                if content != original_content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
print("UI-7 Apply Completed")
