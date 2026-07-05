import os
import re

file_path = r'd:\smartcampus\smartcampus-ai\routes\builder_routes.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "@builder_bp.route('/api/resume/generate-pdf', methods=['POST'])"
end_marker = "@builder_bp.route('/api/resume/builder/save-to-resumes', methods=['POST'])"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

new_pdf_funcs = '''@builder_bp.route('/api/resume/generate-pdf', methods=['POST'])
@jwt_required()
def generate_pdf_endpoint():
    """Generates PDF using the frontend JSON state."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid payload"}), 400
        
    user_data = data.get('student_info', {})
    profile_data = data.get('profile', {})
    projects = data.get('projects', [])
    certs = data.get('certifications', [])
    portfolio_items = data.get('portfolio_items', [])
    template_id = data.get('template_id', 'v2')

    try:
        from utils.pdf_generator import generate_ats_pdf_v2
        pdf_bytes = generate_ats_pdf_v2(user_data, profile_data, projects, certs, portfolio_items, template_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resume_{timestamp}.pdf"
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@builder_bp.route('/api/resume/builder/generate-docx', methods=['POST'])
@jwt_required()
def generate_docx_endpoint():
    """Generates DOCX from builder JSON state."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid payload"}), 400
        
    user_data = data.get('student_info', {})
    profile_data = data.get('profile', {})
    projects = data.get('projects', [])
    certs = data.get('certifications', [])
    template_id = data.get('template_id', 'tpl_prof_03')
    
    try:
        from utils.docx_generator import generate_ats_docx
        docx_bytes = generate_ats_docx(user_data, profile_data, projects, certs, template_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resume_{timestamp}.docx"
        
        return send_file(
            io.BytesIO(docx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

'''

new_content = content[:start_idx] + new_pdf_funcs + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Phase 3 rewrite done')
