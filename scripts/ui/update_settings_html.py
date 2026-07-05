import re

def update_settings_html():
    with open('d:/smartcampus/smartcampus-ai/templates/settings.html', 'r', encoding='utf-8') as f:
        content = f.read()

    new_ui = """            <div id="active-resume-info" class="{{ 'hidden' if not has_resume else '' }}" style="margin-bottom: var(--space-5); padding: var(--space-4); background: rgba(255,255,255,0.03); border-radius: var(--radius-md); ">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                            <h4 style="margin: 0; font-size: 15px; color: var(--text-primary);">Resume Uploaded</h4>
                        </div>
                        <p id="resume-filename" style="margin: 0; font-size: 13px; color: var(--primary);"></p>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 16px;">
                    <button onclick="downloadActiveResume()" class="btn-secondary" style="width: 100%; padding: 8px; font-size: 13px; display: flex; justify-content: center; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Download Original Resume
                    </button>
                    {% if resume_versions and resume_versions|length > 0 %}
                    <a href="/builder?version={{resume_versions[0].version_number}}" class="btn-primary" style="text-decoration: none; text-align: center; width: 100%; padding: 8px; font-size: 13px; display: flex; justify-content: center; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Download Optimized Resume
                    </a>
                    {% endif %}
                    <button onclick="document.getElementById('resume-upload').click()" class="btn-outline" style="width: 100%; padding: 8px; font-size: 13px; display: flex; justify-content: center; align-items: center; gap: 6px;">
                        Replace Original
                    </button>
                </div>
            </div>

            {% if not has_resume %}
            <div id="no-resume-info" class="upload-zone" id="drop-zone" onclick="document.getElementById('resume-upload').click()" style="margin-bottom: 0;">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--primary); margin-bottom: 12px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                <p style="margin: 0 0 4px 0; font-weight: 500;">No Resume Uploaded</p>
                <p class="muted-text" style="margin: 0; font-size: 13px;">Upload a PDF to pre-fill your profile</p>
            </div>
            {% endif %}
            
            <input type="file" id="resume-upload" accept=".pdf,.docx" style="display: none;" onchange="handleResumeUpload(this.files)">
            <div id="upload-status" style="margin-top: 12px; font-size: 13px; text-align: center; color: var(--text-secondary); display: none;">
                <span class="spinner" style="display: inline-block; width: 14px; height: 14px; border: 2px solid var(--primary); border-right-color: transparent; border-radius: 50%; animation: spin 1s linear infinite; vertical-align: middle; margin-right: 6px;"></span>
                Parsing new resume...
            </div>
        </div>
        
        <!-- Versions Section -->
        {% if resume_versions and resume_versions|length > 0 %}
        <div class="card" style="padding: var(--space-6);">
            <h3 class="card-title text-lg font-semibold" style="margin-bottom: var(--space-4);">Optimization Versions</h3>
            <div style="display: flex; flex-direction: column; gap: 12px;">
                {% for v in resume_versions %}
                <div style="background: rgba(255,255,255,0.02); padding: 12px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0; font-size: 14px;">Version {{ v.version_number }}</h4>
                        <p style="margin: 4px 0 0 0; font-size: 12px; color: var(--success);">+{{ v.ats_improvement_score }} ATS Match Score</p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button onclick="restoreVersion({{v.version_number}})" class="btn-secondary" style="font-size: 12px; padding: 4px 8px;">Restore</button>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <!-- Roadmaps Section -->
        {% if roadmaps and roadmaps|length > 0 %}
        <div class="card" style="padding: var(--space-6);">
            <h3 class="card-title text-lg font-semibold" style="margin-bottom: var(--space-4);">Learning Roadmaps</h3>
            <div style="display: flex; flex-direction: column; gap: 12px;">
                {% for r in roadmaps %}
                <div style="background: rgba(255,255,255,0.02); padding: 12px; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h4 style="margin: 0; font-size: 14px;">{{ r.company_name or 'Company' }} - {{ r.job_title or 'Target Role' }}</h4>
                        <span class="badge-item badge-blue" style="font-size: 11px;">v{{ r.roadmap_version }}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <p style="margin: 0; font-size: 12px; color: var(--text-secondary);">ATS: {{r.ats_score}} | Match: {{r.match_score}}</p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <a href="/jd-analyzer?resume_id={{r.resume_id}}&jd_id={{r.jd_id}}" class="btn-secondary" style="font-size: 12px; padding: 4px 8px; text-decoration: none;">View Roadmap</a>
                        <a href="/api/intelligence/roadmap/{{r.id}}/pdf" class="btn-primary" style="font-size: 12px; padding: 4px 8px; text-decoration: none;">Download PDF</a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
    </div>"""

    content = re.sub(r'<div id="active-resume-info" class="{{ \'hidden\' if not has_resume else \'\' }}".*?<!-- Right Column -->.*?</div>\s*</div>\s*</div>', 
                     new_ui + "\n  </div>\n</div>\n</div>", 
                     content, flags=re.DOTALL)
                     
    with open('d:/smartcampus/smartcampus-ai/templates/settings.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_settings_html()
