import os

file_path = r'd:\smartcampus\smartcampus-ai\utils\pdf_generator.py'
with open(file_path, 'a', encoding='utf-8') as f:
    f.write('''
def generate_ats_pdf_v2(user_data, profile_data, projects, certs, portfolio_items, template_id='v2'):
    try:
        from xhtml2pdf import pisa
    except Exception as e:
        raise RuntimeError(f"xhtml2pdf dependency missing. Cannot generate PDF. {e}")

    html_string = render_template(
        "resume_template_v2.html",
        user=user_data,
        profile=profile_data,
        projects=projects,
        certs=certs,
        portfolio_items=portfolio_items,
        template_id=template_id
    )
    
    result_file = BytesIO()
    pisa_status = pisa.CreatePDF(BytesIO(html_string.encode('utf-8')), dest=result_file)
    
    if pisa_status.err:
        raise RuntimeError("PDF generation failed due to xhtml2pdf errors.")
        
    return result_file.getvalue()
''')
