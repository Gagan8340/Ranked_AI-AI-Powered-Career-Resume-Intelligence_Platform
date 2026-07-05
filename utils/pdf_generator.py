from flask import render_template
from io import BytesIO

def generate_ats_pdf(user_data, profile_data, projects, certs, portfolio_items):
    """
    Renders the unified ATS-compliant HTML template with user data,
    and converts it securely into a PDF binary stream using xhtml2pdf.
    """
    try:
        from xhtml2pdf import pisa
    except Exception as e:
        raise RuntimeError(f"xhtml2pdf dependency missing. Cannot generate PDF. {e}")

    # Generate the HTML using the singular ATS print template
    html_string = render_template(
        "ats_print.html",
        user=user_data,
        profile=profile_data,
        projects=projects,
        certs=certs,
        portfolio_items=portfolio_items
    )
    
    result_file = BytesIO()
    # pisa.CreatePDF converts the HTML string to a PDF stream
    pisa_status = pisa.CreatePDF(BytesIO(html_string.encode('utf-8')), dest=result_file)
    
    if pisa_status.err:
        raise RuntimeError("PDF generation failed due to xhtml2pdf errors.")
        
    return result_file.getvalue()
