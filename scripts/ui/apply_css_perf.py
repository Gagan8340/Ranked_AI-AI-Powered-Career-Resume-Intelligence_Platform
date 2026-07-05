import os

base_dir = "d:/smartcampus/smartcampus-ai"
css_path = os.path.join(base_dir, "static/css/main.css")

css_append = """
/* ==========================================================================
   PERFORMANCE & RENDERING STABILIZATION 
   ========================================================================== */

/* 1. Layout Rendering Complexity Reduction */
.dashboard-main, .stats-grid, .action-grid, .content, .chat-messages {
    /* Offload off-screen rendering */
    content-visibility: auto;
    contain: paint layout;
    contain-intrinsic-size: 1px 1000px;
}

/* 2. Optimize CSS Rendering & Blur Costs */
/* Replace heavy drop-shadow filters on non-critical hover states with fast GPU box-shadow */
.card-hover:hover, .stat-card:hover, .action-card:hover, .panel:hover {
    box-shadow: 0 8px 24px -10px rgba(124, 58, 237, 0.4) !important; 
    transform: translateY(-2px) translateZ(0) !important;
}

/* Limit blur intensity on deeply nested components to save rasterizer thread */
.glass-card, .sidebar {
    backdrop-filter: blur(10px) !important; /* Reduced from 16/18px */
    -webkit-backdrop-filter: blur(10px) !important;
}

/* 3. GPU Acceleration for Animations */
.skeleton, .fade-up, .streak-number, .btn-primary, .avatar {
    will-change: transform, opacity;
    /* Force GPU layer compositing */
    transform: translateZ(0);
    backface-visibility: hidden;
}

/* Reduce transition scopes from 'all' to specific properties to avoid repaints */
* {
    transition-property: background-color, border-color, color, fill, stroke, opacity, box-shadow, transform !important;
}

/* 4. Reduced Layout Shifts (CLS) */
img, svg, .chart-area {
    aspect-ratio: auto; /* Fallback */
    overflow: hidden;
}

/* 5. Extreme Performance Fallbacks */
@media (prefers-reduced-motion: reduce) {
    .sidebar { backdrop-filter: none !important; background: var(--bg-sidebar) !important; }
    .glass-card { backdrop-filter: none !important; }
}
"""

if os.path.exists(css_path):
    with open(css_path, "a", encoding="utf-8") as f:
        f.write(css_append)
    print("Performance CSS appended.")
else:
    print("Error: main.css not found.")
