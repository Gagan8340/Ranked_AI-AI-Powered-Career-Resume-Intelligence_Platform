import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'docx'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword'
}

def validate_file(file, max_size_bytes=5 * 1024 * 1024):
    """
    Validates an uploaded file's extension, MIME type, and size.
    Returns (is_valid, error_message).
    """
    if not file or file.filename == '':
        return False, "No file selected"
    
    # 1. File size validation by checking stream length
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)  # Reset stream pointer to beginning
    
    if size > max_size_bytes:
        return False, f"File size exceeds maximum limit of {max_size_bytes / (1024 * 1024):.1f}MB"
    
    # 2. Extension validation
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension '.{ext}' is not allowed. Only PDF and DOCX files are permitted."
    
    # 3. MIME validation
    mime_type = file.content_type
    if mime_type not in ALLOWED_MIME_TYPES:
        return False, f"MIME type '{mime_type}' is not allowed. Only PDF and DOCX files are permitted."
        
    return True, None
