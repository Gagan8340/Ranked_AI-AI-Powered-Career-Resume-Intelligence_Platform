import os
import tempfile
import subprocess
import shutil
from flask import Blueprint, jsonify, request, send_file, current_app, abort
from flask_jwt_extended import jwt_required

latex_bp = Blueprint('latex_routes', __name__)

LATEX_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'latex-templates')
RESUME_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resume-templates')

@latex_bp.route('/api/latex/templates', methods=['GET'])
@jwt_required()
def get_templates():
    """List all available latex templates."""
    try:
        if not os.path.exists(LATEX_TEMPLATES_DIR):
            return jsonify({'error': 'Templates directory not found'}), 404
            
        templates = []
        for filename in os.listdir(LATEX_TEMPLATES_DIR):
            if filename.endswith('.tex'):
                base_name = filename[:-4]
                templates.append({
                    'id': base_name,
                    'name': base_name.replace('_', ' '),
                    'filename': filename
                })
        
        # Sort templates by name (or ID)
        templates.sort(key=lambda x: x['id'])
        return jsonify({'templates': templates}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@latex_bp.route('/api/latex/template/<template_id>', methods=['GET'])
@jwt_required()
def get_template_content(template_id):
    """Get the LaTeX code for a specific template."""
    try:
        filename = f"{template_id}.tex"
        filepath = os.path.join(LATEX_TEMPLATES_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Template not found'}), 404
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if a pre-compiled PDF exists
        pdf_filename = f"{template_id}.pdf"
        pdf_path = os.path.join(RESUME_TEMPLATES_DIR, pdf_filename)
        has_default_pdf = os.path.exists(pdf_path)
        
        return jsonify({
            'id': template_id,
            'content': content,
            'has_default_pdf': has_default_pdf,
            'pdf_url': f"/api/latex/pdf/{template_id}.pdf" if has_default_pdf else None
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@latex_bp.route('/api/latex/pdf/<filename>', methods=['GET'])
@jwt_required()
def get_default_pdf(filename):
    """Serve a pre-compiled PDF from the resume-templates directory."""
    try:
        if not filename.endswith('.pdf'):
            return abort(400, "Invalid file type")
            
        filepath = os.path.join(RESUME_TEMPLATES_DIR, filename)
        if not os.path.exists(filepath):
            return abort(404, "PDF not found")
            
        return send_file(filepath, mimetype='application/pdf')
    except Exception as e:
        return abort(500, str(e))

@latex_bp.route('/api/latex/compile', methods=['POST'])
@jwt_required()
def compile_latex():
    """Compile LaTeX code to PDF and return it."""
    try:
        data = request.json
        if not data or 'latex_code' not in data:
            return jsonify({'error': 'No LaTeX code provided'}), 400
            
        latex_code = data['latex_code']
        
        # Create a temporary directory to avoid clutter and handle concurrent requests
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_filepath = os.path.join(temp_dir, 'main.tex')
            pdf_filepath = os.path.join(temp_dir, 'main.pdf')
            
            with open(tex_filepath, 'w', encoding='utf-8') as f:
                f.write(latex_code)
                
            # Run pdflatex. Use -interaction=nonstopmode to avoid hanging on errors
            try:
                pdflatex_path = shutil.which('pdflatex')
                if not pdflatex_path:
                    # Fallback to common MiKTeX install path on Windows
                    fallback_path = r'C:\Users\sanag\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe'
                    if os.path.exists(fallback_path):
                        pdflatex_path = fallback_path
                
                if pdflatex_path:
                    cmd = [pdflatex_path, '-interaction=nonstopmode', '-output-directory', temp_dir, tex_filepath]
                    # First run (give it 45 seconds for first-time package downloads)
                    process1 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
                    # Second run (optional, but good for references)
                    process2 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
                    
                    if not os.path.exists(pdf_filepath):
                        # Compilation failed, return the log
                        log_path = os.path.join(temp_dir, 'main.log')
                        error_log = "Unknown error during compilation."
                        if os.path.exists(log_path):
                            with open(log_path, 'r', encoding='utf-8', errors='ignore') as log_file:
                                error_log = log_file.read()
                        return jsonify({'error': 'LaTeX compilation failed', 'log': error_log, 'stdout': process1.stdout.decode('utf-8', errors='ignore')}), 400
                        
                    # If successful, read the PDF into memory so we can return it after the temp dir is deleted
                    with open(pdf_filepath, 'rb') as f:
                        pdf_data = f.read()
                        
                    import io
                    return send_file(
                        io.BytesIO(pdf_data),
                        mimetype='application/pdf',
                        as_attachment=False,
                        download_name='compiled.pdf'
                    )
                else:
                    return jsonify({'error': 'pdflatex executable not found on the server. Please ensure a LaTeX distribution is installed and in the system PATH.'}), 500
                    
            except subprocess.TimeoutExpired:
                return jsonify({'error': 'LaTeX compilation timed out'}), 408
            except FileNotFoundError:
                return jsonify({'error': 'pdflatex executable not found on the server. Please ensure a LaTeX distribution is installed and in the system PATH.'}), 500
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
