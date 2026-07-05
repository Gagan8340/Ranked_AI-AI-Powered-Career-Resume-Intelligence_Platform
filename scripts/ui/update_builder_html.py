import os

file_path = r'd:\smartcampus\smartcampus-ai\templates\resume_builder.html'

html_content = r'''{% set active_page = "resume_builder" %}
{% extends "base.html" %}

{% block content %}
<div class="builder-v2-layout">
    
    <!-- LEFT PANEL: Sidebar Navigation -->
    <div class="sidebar-panel card">
        <div class="sidebar-header">
            <h3>Sections</h3>
        </div>
        <div class="sidebar-nav" id="sidebar-nav">
            <!-- Populated by JS -->
        </div>
    </div>

    <!-- CENTER PANEL: Editor Workspace -->
    <div class="editor-panel card">
        <div class="editor-header flex-between">
            <h3 id="current-section-title">Basic Information</h3>
            <div style="display: flex; gap: 10px; align-items: center;">
                <div id="save-status" style="font-size: 12px; color: var(--success); opacity: 0; transition: opacity 0.3s;">Saved</div>
                <button id="save-draft-btn" class="btn-secondary" style="padding: 6px 12px; font-size: 13px;">💾 Save Draft</button>
            </div>
        </div>
        
        <div class="editor-content" id="editor-workspace">
            <!-- Dynamic workspace populated by JS -->
        </div>
    </div>

    <!-- RIGHT PANEL: Live Preview -->
    <div class="preview-panel card">
        <div class="preview-header flex-between">
            <div style="font-weight: 600; color: #333;">Live Preview</div>
            <div style="display: flex; gap: 10px;">
                <button id="download-pdf-btn" class="btn-primary" style="padding: 6px 12px; font-size: 13px;">⬇️ Download PDF</button>
            </div>
        </div>
        <div class="preview-content">
            <div id="live-preview-container" class="preview-document">
                <!-- HTML Injected Here by JS -->
            </div>
        </div>
    </div>
</div>

<style>
/* V2 Builder Layout */
.builder-v2-layout { display: grid; grid-template-columns: 240px 1fr 450px; gap: 20px; height: 88vh; }
.card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-subtle); display: flex; flex-direction: column; overflow: hidden; }

/* Sidebar */
.sidebar-header { padding: 15px; border-bottom: 1px solid var(--border-subtle); }
.sidebar-nav { flex: 1; overflow-y: auto; padding: 10px; }
.nav-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; margin-bottom: 4px; border-radius: 6px; cursor: pointer; color: var(--text-secondary); font-size: 13px; font-weight: 500; transition: all 0.2s; }
.nav-item:hover { background: rgba(0,0,0,0.05); color: var(--text-primary); }
.nav-item.active { background: rgba(109, 40, 217, 0.1); color: var(--primary); font-weight: 600; }
.nav-item .toggle-eye { opacity: 0.5; cursor: pointer; }
.nav-item .toggle-eye:hover { opacity: 1; color: var(--primary); }
.nav-item .toggle-eye.hidden { opacity: 0.3; text-decoration: line-through; }

/* Editor */
.editor-header { padding: 15px 20px; border-bottom: 1px solid var(--border-subtle); background: rgba(255,255,255,0.02); }
.editor-content { flex: 1; overflow-y: auto; padding: 20px; }

/* Preview */
.preview-header { padding: 15px 20px; border-bottom: 1px solid var(--border-subtle); background: white; }
.preview-content { flex: 1; overflow-y: auto; padding: 20px; display: flex; justify-content: center; background: #e2e8f0; }
.preview-document { width: 100%; max-width: 800px; min-height: 1000px; background: white; box-shadow: 0 10px 25px rgba(0,0,0,0.1); border-radius: 4px; padding: 40px; font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10pt; color: #000; }

/* Dynamic Forms */
.form-group { margin-bottom: 15px; }
.input-label { display: block; margin-bottom: 5px; font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.custom-input { width: 100%; padding: 10px; background: rgba(0,0,0,0.03); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-primary); font-family: inherit; }
.item-card { background: rgba(0,0,0,0.02); border: 1px solid var(--border-subtle); padding: 15px; border-radius: 8px; margin-bottom: 15px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }

/* Empty State */
.empty-state-box { text-align: center; padding: 40px 20px; border: 2px dashed var(--border-subtle); border-radius: 8px; color: var(--text-secondary); }
.empty-state-box p { margin-bottom: 20px; font-size: 14px; }

/* Preview CSS internal */
.preview-document .name { font-size: 20pt; font-weight: bold; text-align: center; text-transform: uppercase; margin-bottom: 5px; }
.preview-document .contact { font-size: 10pt; text-align: center; margin-bottom: 15px; }
.preview-document .section-title { font-size: 12pt; font-weight: bold; text-transform: uppercase; border-bottom: 1px solid #000; margin-top: 12px; margin-bottom: 8px; padding-bottom: 2px; }
.preview-document .item-row { display: flex; justify-content: space-between; align-items: baseline; }
.preview-document .item-title { font-weight: bold; font-size: 10.5pt; }
.preview-document .item-subtitle { font-style: italic; font-size: 10pt; margin-bottom: 3px; }
.preview-document .item-desc { margin-top: 3px; font-size: 10pt; }
.preview-document ul { padding-left: 18px; margin: 4px 0; }
</style>

<script>
// SECTIONS CONFIGURATION
const SECTIONS = [
    { id: 'basic_information', title: 'Basic Information', icon: '👤', type: 'fixed' },
    { id: 'professional_summary', title: 'Professional Summary', icon: '📝', type: 'fixed' },
    { id: 'skills', title: 'Skills', icon: '⚡', type: 'list' },
    { id: 'education', title: 'Academics', icon: '🎓', type: 'list' },
    { id: 'experience', title: 'Work Experience', icon: '💼', type: 'list' },
    { id: 'projects', title: 'Projects', icon: '📁', type: 'custom_projects' },
    { id: 'certifications', title: 'Certifications', icon: '📜', type: 'custom_certs' },
    { id: 'awards', title: 'Awards', icon: '🏆', type: 'portfolio', p_type: 'AWARD' },
    { id: 'publications', title: 'Publications', icon: '📄', type: 'portfolio', p_type: 'PUBLICATION' },
    { id: 'volunteering', title: 'Volunteering', icon: '❤️', type: 'portfolio', p_type: 'VOLUNTEERING' },
    { id: 'competitions', title: 'Competitions', icon: '🏅', type: 'portfolio', p_type: 'COMPETITION' },
    { id: 'workshops', title: 'Conferences & Workshops', icon: '🎤', type: 'portfolio', p_type: 'WORKSHOP' },
    { id: 'tests', title: 'Tests', icon: '📊', type: 'portfolio', p_type: 'TEST' },
    { id: 'patents', title: 'Patents', icon: '©️', type: 'portfolio', p_type: 'PATENT' },
    { id: 'scholarships', title: 'Scholarships', icon: '₹', type: 'portfolio', p_type: 'SCHOLARSHIP' },
    { id: 'extracurricular', title: 'Extra Curricular', icon: '🎭', type: 'portfolio', p_type: 'EXTRACURRICULAR' }
];

let activeSection = 'basic_information';

let state = {
    student_info: {},
    profile: { professional_summary: "", linkedin: "", github: "", portfolio: "", skills: [], achievements: [], education: [], experience: [], hidden_sections: {} },
    projects: [],
    certifications: [],
    portfolio_items: []
};

// INIT
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const res = await window.apiFetch('/api/builder/data');
        if(res.ok) {
            const data = await res.json();
            state.student_info = data.student_info || {};
            state.profile = { ...state.profile, ...data.profile };
            if(typeof state.profile.hidden_sections === 'string') state.profile.hidden_sections = JSON.parse(state.profile.hidden_sections || '{}');
            state.projects = data.projects || [];
            state.certifications = data.certifications || [];
            state.portfolio_items = data.portfolio_items || [];
            
            renderSidebar();
            renderWorkspace();
            renderLocalPreview();
        }
    } catch(e) { console.error("Init failed", e); }
});

// SIDEBAR
function renderSidebar() {
    const nav = document.getElementById('sidebar-nav');
    nav.innerHTML = SECTIONS.map(sec => {
        const isHidden = state.profile.hidden_sections[sec.id];
        return `<div class="nav-item ${activeSection === sec.id ? 'active' : ''}" onclick="selectSection('${sec.id}')">
            <span>${sec.icon} ${sec.title}</span>
            <span class="toggle-eye ${isHidden ? 'hidden' : ''}" onclick="toggleVisibility(event, '${sec.id}')">${isHidden ? '👁️‍🗨️' : '👁️'}</span>
        </div>`;
    }).join('');
}

window.selectSection = (id) => {
    activeSection = id;
    renderSidebar();
    renderWorkspace();
};

window.toggleVisibility = (e, id) => {
    e.stopPropagation();
    state.profile.hidden_sections[id] = !state.profile.hidden_sections[id];
    renderSidebar();
    handleUpdate();
};

// WORKSPACE
function renderWorkspace() {
    const sec = SECTIONS.find(s => s.id === activeSection);
    document.getElementById('current-section-title').innerText = sec.title;
    
    const ws = document.getElementById('editor-workspace');
    
    if (sec.id === 'basic_information') {
        ws.innerHTML = `
            <div class="form-group"><label class="input-label">LinkedIn URL</label><input class="custom-input" id="inp-linkedin" value="${state.profile.linkedin || ''}" onkeyup="updateState('profile', 'linkedin', this.value)"></div>
            <div class="form-group"><label class="input-label">GitHub URL</label><input class="custom-input" id="inp-github" value="${state.profile.github || ''}" onkeyup="updateState('profile', 'github', this.value)"></div>
            <div class="form-group"><label class="input-label">Portfolio URL</label><input class="custom-input" id="inp-portfolio" value="${state.profile.portfolio || ''}" onkeyup="updateState('profile', 'portfolio', this.value)"></div>
        `;
        return;
    }
    
    if (sec.id === 'professional_summary') {
        ws.innerHTML = `
            <div class="form-group">
                <label class="input-label">Summary</label>
                <textarea class="custom-input" rows="8" onkeyup="updateState('profile', 'professional_summary', this.value)">${state.profile.professional_summary || ''}</textarea>
            </div>
        `;
        return;
    }
    
    if (sec.type === 'list') {
        const list = state.profile[sec.id] || [];
        ws.innerHTML = `
            <div style="margin-bottom: 20px;">
                <input class="custom-input" placeholder="Type and press Enter to add..." id="inp-list-add" onkeypress="handleListAdd(event, '${sec.id}')">
            </div>
            <div style="display:flex; flex-direction:column; gap:10px;">
                ${list.length === 0 ? renderEmptyState(sec) : list.map((item, idx) => `
                    <div class="item-card flex-between" style="padding: 10px 15px; margin-bottom:0;">
                        <span style="font-size:13px;">${item}</span>
                        <button class="btn-ghost" style="color:var(--danger); padding:0;" onclick="removeListItem('${sec.id}', ${idx})">Remove</button>
                    </div>
                `).join('')}
            </div>
        `;
        return;
    }
    
    if (sec.type === 'custom_projects') {
        ws.innerHTML = `
            <div class="flex-between mb-4">
                <span>Manage your projects here.</span>
                <button class="btn-primary" onclick="addProject()">+ Add Project</button>
            </div>
            ${state.projects.length === 0 ? renderEmptyState(sec) : state.projects.map((p, idx) => `
                <div class="item-card">
                    <div class="flex-between mb-2">
                        <strong>Project ${idx+1}</strong>
                        <button class="btn-ghost text-danger" style="padding:0;" onclick="removeProject(${idx})">Delete</button>
                    </div>
                    <input class="custom-input mb-2" placeholder="Project Name" value="${p.project_name || ''}" onkeyup="updateProject(${idx}, 'project_name', this.value)">
                    <input class="custom-input mb-2" placeholder="Tech Stack" value="${p.tech_stack || ''}" onkeyup="updateProject(${idx}, 'tech_stack', this.value)">
                    <div style="display:flex; gap:10px;">
                        <input class="custom-input mb-2" placeholder="GitHub URL" value="${p.github_url || ''}" onkeyup="updateProject(${idx}, 'github_url', this.value)">
                        <input class="custom-input mb-2" placeholder="Live URL" value="${p.live_url || ''}" onkeyup="updateProject(${idx}, 'live_url', this.value)">
                    </div>
                    <textarea class="custom-input" placeholder="Description" rows="3" onkeyup="updateProject(${idx}, 'description', this.value)">${p.description || ''}</textarea>
                </div>
            `).join('')}
        `;
        return;
    }
    
    if (sec.type === 'custom_certs') {
        ws.innerHTML = `
            <div class="flex-between mb-4">
                <span>Manage your certifications here.</span>
                <button class="btn-primary" onclick="addCert()">+ Add Certification</button>
            </div>
            ${state.certifications.length === 0 ? renderEmptyState(sec) : state.certifications.map((c, idx) => `
                <div class="item-card">
                    <div class="flex-between mb-2">
                        <strong>Certification ${idx+1}</strong>
                        <button class="btn-ghost text-danger" style="padding:0;" onclick="removeCert(${idx})">Delete</button>
                    </div>
                    <input class="custom-input mb-2" placeholder="Name" value="${c.name || ''}" onkeyup="updateCert(${idx}, 'name', this.value)">
                    <div style="display:flex; gap:10px;">
                        <input class="custom-input mb-2" placeholder="Issuer" value="${c.issuer || ''}" onkeyup="updateCert(${idx}, 'issuer', this.value)">
                        <input class="custom-input mb-2" type="date" value="${c.issue_date || ''}" onchange="updateCert(${idx}, 'issue_date', this.value)">
                    </div>
                    <input class="custom-input mb-2" placeholder="URL" value="${c.certificate_url || ''}" onkeyup="updateCert(${idx}, 'certificate_url', this.value)">
                </div>
            `).join('')}
        `;
        return;
    }
    
    if (sec.type === 'portfolio') {
        const items = state.portfolio_items.filter(i => i.item_type === sec.p_type).sort((a,b)=> a.display_order - b.display_order);
        ws.innerHTML = `
            <div class="flex-between mb-4">
                <span>Manage your ${sec.title}.</span>
                <button class="btn-primary" onclick="addPortfolioItem('${sec.p_type}')">+ Add New</button>
            </div>
            ${items.length === 0 ? renderEmptyState(sec) : items.map((item) => {
                const globalIdx = state.portfolio_items.findIndex(i => i === item);
                return `
                <div class="item-card">
                    <div class="flex-between mb-2">
                        <strong>${sec.title} Item</strong>
                        <button class="btn-ghost text-danger" style="padding:0;" onclick="removePortfolioItem(${globalIdx})">Delete</button>
                    </div>
                    <input class="custom-input mb-2" placeholder="Title" value="${item.title || ''}" onkeyup="updatePortfolioItem(${globalIdx}, 'title', this.value)">
                    <div style="display:flex; gap:10px;">
                        <input class="custom-input mb-2" placeholder="Organization" value="${item.organization || ''}" onkeyup="updatePortfolioItem(${globalIdx}, 'organization', this.value)">
                        <input class="custom-input mb-2" placeholder="Associated With" value="${item.associated_with || ''}" onkeyup="updatePortfolioItem(${globalIdx}, 'associated_with', this.value)">
                    </div>
                    <div style="display:flex; gap:10px;">
                        <input class="custom-input mb-2" type="date" value="${item.start_date || ''}" onchange="updatePortfolioItem(${globalIdx}, 'start_date', this.value)">
                        <input class="custom-input mb-2" type="date" value="${item.end_date || ''}" onchange="updatePortfolioItem(${globalIdx}, 'end_date', this.value)">
                    </div>
                    <input class="custom-input mb-2" placeholder="URL" value="${item.url || ''}" onkeyup="updatePortfolioItem(${globalIdx}, 'url', this.value)">
                    <textarea class="custom-input" placeholder="Description" rows="3" onkeyup="updatePortfolioItem(${globalIdx}, 'description', this.value)">${item.description || ''}</textarea>
                </div>
            `}).join('')}
        `;
        return;
    }
}

function renderEmptyState(sec) {
    return `
        <div class="empty-state-box">
            <div style="font-size:30px; margin-bottom:10px;">${sec.icon}</div>
            <p>No ${sec.title.toLowerCase()} added yet.<br>This section will not appear on your resume.</p>
            <!-- Add From Existing is conceptually automatic via profile sync, but a manual trigger can be built here -->
        </div>
    `;
}

// STATE HANDLERS
window.updateState = (obj, key, val) => { state[obj][key] = val; handleUpdate(); };
window.handleListAdd = (e, listKey) => {
    if(e.key === 'Enter' && e.target.value.trim()) {
        state.profile[listKey].push(e.target.value.trim());
        e.target.value = '';
        renderWorkspace();
        handleUpdate();
    }
};
window.removeListItem = (listKey, idx) => { state.profile[listKey].splice(idx, 1); renderWorkspace(); handleUpdate(); };

window.addProject = () => { state.projects.push({}); renderWorkspace(); handleUpdate(); };
window.removeProject = (idx) => { state.projects.splice(idx, 1); renderWorkspace(); handleUpdate(); };
window.updateProject = (idx, k, v) => { state.projects[idx][k] = v; handleUpdate(); };

window.addCert = () => { state.certifications.push({}); renderWorkspace(); handleUpdate(); };
window.removeCert = (idx) => { state.certifications.splice(idx, 1); renderWorkspace(); handleUpdate(); };
window.updateCert = (idx, k, v) => { state.certifications[idx][k] = v; handleUpdate(); };

window.addPortfolioItem = (type) => { 
    state.portfolio_items.push({ item_type: type, display_order: state.portfolio_items.length, is_visible: 1 }); 
    renderWorkspace(); 
    handleUpdate(); 
};
window.removePortfolioItem = (idx) => { state.portfolio_items.splice(idx, 1); renderWorkspace(); handleUpdate(); };
window.updatePortfolioItem = (idx, k, v) => { state.portfolio_items[idx][k] = v; handleUpdate(); };

// PREVIEW GENERATOR (CLIENT SIDE RENDER)
let previewTimeout;
function handleUpdate() {
    clearTimeout(previewTimeout);
    previewTimeout = setTimeout(() => { renderLocalPreview(); }, 200);
}

function renderLocalPreview() {
    const p = state.profile;
    const h = p.hidden_sections || {};
    
    let html = `
        <div class="name">${state.student_info.name || 'Your Name'}</div>
        <div class="contact">
            ${state.student_info.email || 'email@example.com'} | ${state.student_info.phone || 'Phone'}
            ${p.linkedin ? ` | ${p.linkedin}` : ''}
            ${p.github ? ` | ${p.github}` : ''}
            ${p.portfolio ? ` | ${p.portfolio}` : ''}
        </div>
    `;
    
    if (p.professional_summary && !h.basic_information && !h.professional_summary) {
        html += `<div class="section-title">Professional Summary</div><p>${p.professional_summary}</p>`;
    }
    
    if (p.education && p.education.length && !h.education) {
        html += `<div class="section-title">Education</div><ul>${p.education.map(e => `<li>${e}</li>`).join('')}</ul>`;
    }
    
    if (p.experience && p.experience.length && !h.experience) {
        html += `<div class="section-title">Work Experience</div><ul>${p.experience.map(e => `<li>${e}</li>`).join('')}</ul>`;
    }
    
    if (state.projects && state.projects.length && !h.projects) {
        html += `<div class="section-title">Projects</div>`;
        state.projects.forEach(pr => {
            html += `<div class="item-row"><div class="item-title">${pr.project_name || 'Project'}</div><div>${pr.github_url ? `GitHub: ${pr.github_url}` : ''}</div></div>`;
            if (pr.tech_stack) html += `<div class="item-subtitle">Tech Stack: ${pr.tech_stack}</div>`;
            if (pr.description) html += `<div class="item-desc">${pr.description}</div>`;
            html += `<div style="margin-bottom:10px;"></div>`;
        });
    }
    
    if (p.skills && p.skills.length && !h.skills) {
        html += `<div class="section-title">Skills</div><p>${p.skills.join(', ')}</p>`;
    }
    
    if (state.certifications && state.certifications.length && !h.certifications) {
        html += `<div class="section-title">Certifications</div>`;
        state.certifications.forEach(c => {
            html += `<div class="item-row"><div class="item-title">${c.name || 'Certification'}</div><div>${c.issue_date || ''}</div></div>`;
            if (c.issuer) html += `<div class="item-subtitle">${c.issuer}</div>`;
            html += `<div style="margin-bottom:10px;"></div>`;
        });
    }
    
    // Portfolio Items Grouping
    const grouped = {};
    state.portfolio_items.forEach(i => {
        if (!i.is_visible) return;
        if (!grouped[i.item_type]) grouped[i.item_type] = [];
        grouped[i.item_type].push(i);
    });
    
    for (const [type, items] of Object.entries(grouped)) {
        const secDef = SECTIONS.find(s => s.p_type === type);
        const secId = secDef ? secDef.id : type.toLowerCase();
        if (h[secId]) continue;
        
        html += `<div class="section-title">${secDef ? secDef.title : type}</div>`;
        items.sort((a,b)=>a.display_order-b.display_order).forEach(item => {
            html += `<div class="item-row"><div class="item-title">${item.title || 'Item'}</div><div>${item.start_date || ''} ${item.end_date ? '- '+item.end_date : ''}</div></div>`;
            if (item.organization || item.associated_with) {
                html += `<div class="item-subtitle">${item.organization||''} ${item.organization&&item.associated_with?' | ':''} ${item.associated_with||''}</div>`;
            }
            if (item.description) html += `<div class="item-desc">${item.description}</div>`;
            html += `<div style="margin-bottom:10px;"></div>`;
        });
    }
    
    document.getElementById('live-preview-container').innerHTML = html;
}

// SAVE & EXPORT
document.getElementById('save-draft-btn').addEventListener('click', async () => {
    try {
        const res = await window.apiFetch('/api/builder/save', { method: 'POST', body: JSON.stringify(state) });
        if(res.ok) {
            const s = document.getElementById('save-status');
            s.style.opacity = 1; setTimeout(() => s.style.opacity = 0, 2000);
        }
    } catch(e) { alert("Save failed."); }
});

document.getElementById('download-pdf-btn').addEventListener('click', async () => {
    document.getElementById('save-draft-btn').click();
    try {
        const res = await window.apiFetch('/api/resume/generate-pdf', { method: 'POST', body: JSON.stringify({...state, template_id: 'v2'}) });
        if(res.ok) {
            const blob = await res.blob();
            const a = document.createElement('a');
            a.href = window.URL.createObjectURL(blob);
            a.download = `resume_v2.pdf`;
            a.click();
        } else alert("PDF generation failed");
    } catch(e) { alert("Error downloading PDF"); }
});

</script>
{% endblock %}
