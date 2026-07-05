import fitz  # PyMuPDF
import docx

def extract_resume_text(file_stream, file_ext):
    """
    Extracts text from a PDF or DOCX file stream.
    Returns (extracted_text, is_scanned)
    
    file_stream: Werkzeug FileStorage or BytesIO
    file_ext: 'pdf' or 'docx'
    """
    text = ""
    is_scanned = False
    
    try:
        # Read the stream content
        stream_content = file_stream.read()
        
        # VERY IMPORTANT: Reset the stream pointer back to 0 
        # so Cloudinary or other processors can read it again afterwards!
        file_stream.seek(0)

        if file_ext == 'pdf':
            # Load PDF from memory bytes
            doc = fitz.open(stream=stream_content, filetype="pdf")
            for page in doc:
                text += page.get_text()
            doc.close()
            
        elif file_ext == 'docx':
            from io import BytesIO
            doc = docx.Document(BytesIO(stream_content))
            for para in doc.paragraphs:
                text += para.text + "\n"
                
        # Clean up whitespace
        text = text.strip()
        
        # Scanned PDF Detection:
        # If the extracted text is less than 100 characters, it's highly likely
        # an image-based/scanned PDF without an OCR text layer.
        if len(text) < 100:
            is_scanned = True
            
        return text, is_scanned
        
    except Exception as e:
        raise Exception(f"Failed to parse resume: {str(e)}")
