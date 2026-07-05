import os

base_dir = "d:/smartcampus/smartcampus-ai"
css_path = os.path.join(base_dir, "static/css/main.css")

css_append = """
/* Responsive QA & Stabilization Fixes */

/* 1. Dashboard Responsiveness */
@media (max-width: 768px) {
    .dashboard-grid-12, .stats-grid, .action-grid {
        display: flex !important;
        flex-direction: column !important;
        gap: var(--space-4) !important;
    }
    .widget-card, .stat-card, .col-3, .col-4, .col-5, .col-7, .col-8 {
        width: 100% !important;
        max-width: 100% !important;
        margin-bottom: var(--space-2) !important;
    }
    .analytics-chart svg, .chart-area {
        width: 100% !important;
        height: auto !important;
    }
    .planner-actions {
        flex-direction: column;
        gap: var(--space-2);
    }
    .planner-actions button {
        width: 100%;
    }
}

/* 2. Quiz Responsiveness & Sticky Timer */
.quiz-timer-container {
    position: sticky;
    top: 70px;
    z-index: 40;
    backdrop-filter: blur(12px);
    background: rgba(11, 16, 32, 0.85);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: var(--space-4);
}
@media (max-width: 768px) {
    .quiz-options button {
        padding: var(--space-4);
        min-height: 60px;
        font-size: var(--text-md);
        touch-action: manipulation;
    }
    .quiz-navigation {
        flex-direction: column;
        gap: var(--space-3);
    }
    .quiz-navigation button {
        width: 100%;
    }
}

/* 3. Chatbot Responsiveness */
.chatbot-container {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 80px);
    overflow: hidden;
}
.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-4);
    scroll-behavior: smooth;
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
}
.chat-input-area {
    position: sticky;
    bottom: 0;
    background: var(--bg-app);
    padding: var(--space-4);
    border-top: 1px solid var(--border-subtle);
    z-index: 40;
}
@media (max-width: 768px) {
    .ai-suggestions {
        display: flex;
        overflow-x: auto;
        padding-bottom: var(--space-2);
        white-space: nowrap;
        -webkit-overflow-scrolling: touch;
    }
    .ai-suggestions::-webkit-scrollbar {
        display: none;
    }
}

/* 4. EduLingo Responsiveness */
.flashcard-container {
    perspective: 1000px;
    width: 100%;
    max-width: 400px;
    margin: 0 auto;
    touch-action: pan-y pinch-zoom;
}
@media (max-width: 768px) {
    .flashcard {
        min-height: 250px;
    }
    .voice-practice-controls {
        flex-direction: column;
        align-items: center;
        gap: var(--space-4);
    }
    .voice-btn {
        width: 80px;
        height: 80px;
        border-radius: 50%;
    }
}

/* 5. Performance Optimization & Layout Shifts */
img, svg {
    max-width: 100%;
    height: auto;
}
.skeleton {
    will-change: background-position;
}
.fade-up {
    will-change: transform, opacity;
}
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}

/* 6. Sidebar Mobile Drawer Fixes */
.sidebar.open {
    box-shadow: 20px 0 50px rgba(0, 0, 0, 0.5);
}
"""

if os.path.exists(css_path):
    with open(css_path, "a", encoding="utf-8") as f:
        f.write(css_append)
    print("Stabilization CSS appended.")
else:
    print("Error: main.css not found.")
