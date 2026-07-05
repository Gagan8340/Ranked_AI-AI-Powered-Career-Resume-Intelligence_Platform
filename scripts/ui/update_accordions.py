import re

with open('templates/settings.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Move toggleAccordion from <style> to <script>
script_match = re.search(r'function toggleAccordion\(header\) \{.*?\}\n', content, re.DOTALL)
if script_match:
    func_str = script_match.group(0)
    content = content.replace(func_str, '') # Remove from style
    # Add it to the <script> block at the end
    content = content.replace('<script>', '<script>\n' + func_str)

# 2. Add 'collapsed' to existing accordions so they start closed
# For content:
content = re.sub(r'class="accordion-content"', 'class="accordion-content collapsed"', content)
# For icon:
content = re.sub(r'class="accordion-icon"', 'class="accordion-icon collapsed"', content)
# Make sure any that were ALREADY collapsed don't end up with "collapsed collapsed"
content = content.replace('collapsed collapsed', 'collapsed')

# 3. Add accordion wrapper to Profile Strength
profile_strength_old = '''<div style="display: flex; align-items: center; gap: 8px; justify-content: center; margin-bottom: 16px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--primary);"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                <h3 class="card-title text-lg font-semibold" style="margin: 0;">Profile Strength</h3>
            </div>'''
profile_strength_new = '''<div class="accordion-header" onclick="toggleAccordion(this)" style="display: flex; justify-content: space-between; align-items: center; cursor: pointer; margin-bottom: 0;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--primary);"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    <h3 class="card-title text-lg font-semibold" style="margin: 0;">Profile Strength</h3>
                </div>
                <svg class="accordion-icon collapsed" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transition: transform 0.3s ease;"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </div>
            <div class="accordion-content collapsed" style="margin-top: 16px;">'''

content = content.replace(profile_strength_old, profile_strength_new)
content = content.replace('</div>\n\n        <!-- Resume Section -->', '</div></div>\n\n        <!-- Resume Section -->')

# 4. Add accordion wrapper to My Roadmaps
roadmaps_old = '<h3 class="card-title text-lg font-semibold" style="margin-bottom: var(--space-4);">My Roadmaps</h3>'
roadmaps_new = '''<div class="accordion-header" onclick="toggleAccordion(this)" style="display: flex; justify-content: space-between; align-items: center; cursor: pointer; margin-bottom: 0;">
                <h3 class="card-title text-lg font-semibold" style="margin: 0;">My Roadmaps</h3>
                <svg class="accordion-icon collapsed" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transition: transform 0.3s ease;"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </div>
            <div class="accordion-content collapsed" style="margin-top: 16px;">'''

content = content.replace(roadmaps_old, roadmaps_new)
# Need to close the accordion-content div for My Roadmaps. It's right before </div><!-- Right Column --> or something similar.
# Let's find the end of My Roadmaps card.
# The card ends after:
#                 </div>
#             {% endif %}
#         </div>

# We can replace:
#             {% endif %}
#         </div>
# With:
#             {% endif %}
#             </div>
#         </div>

content = content.replace('            {% endif %}\n        </div>\n        \n    </div>\n</div>', '            {% endif %}\n            </div>\n        </div>\n        \n    </div>\n</div>')

# 5. Make sure the headers for Personal Information, Professional Summary, etc. have margin-bottom: 0 instead of var(--space-4)
content = content.replace('margin-bottom: var(--space-4);', 'margin-bottom: 0;')
# Wait, this might affect other headers. 
# We should specifically target the accordion headers.
content = content.replace('cursor: pointer; margin-bottom: var(--space-4);', 'cursor: pointer; margin-bottom: 0;')


with open('templates/settings.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated settings.html accordions successfully!")
