import re

def append_endpoints():
    with open('d:/smartcampus/smartcampus-ai/routes/intelligence_routes.py', 'a', encoding='utf-8') as f:
        f.write("""

@intelligence_bp.route('/api/intelligence/roadmap/<int:roadmap_id>/status', methods=['POST'])
@jwt_required()
def toggle_roadmap_status(roadmap_id):
    user_id = get_jwt_identity()
    data = request.json
    status = data.get('status')
    
    if status not in ['active', 'archived', 'completed']:
        return jsonify({"error": "Invalid status"}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE roadmaps SET status = %s WHERE id = %s AND user_id = %s", (status, roadmap_id, user_id))
            if cursor.rowcount == 0:
                return jsonify({"error": "Roadmap not found"}), 404
        conn.commit()
        return jsonify({"message": "Status updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@intelligence_bp.route('/api/intelligence/roadmap/<int:roadmap_id>/pdf', methods=['GET'])
@jwt_required()
def export_roadmap_pdf(roadmap_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(\"\"\"
                SELECT r.*, s.name as student_name 
                FROM roadmaps r 
                JOIN students s ON r.user_id = s.id 
                WHERE r.id = %s AND r.user_id = %s
            \"\"\", (roadmap_id, user_id))
            roadmap_rec = cursor.fetchone()
            
            if not roadmap_rec:
                return jsonify({"error": "Roadmap not found"}), 404
                
        # Generate PDF using reportlab (simplified structure)
        from flask import send_file
        import io
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        
        c.drawString(50, 750, f"Career Learning Roadmap: {roadmap_rec.get('job_title', 'Target Role')}")
        c.setFont("Helvetica", 12)
        c.drawString(50, 730, f"Student: {roadmap_rec.get('student_name')}")
        c.drawString(50, 710, f"Company: {roadmap_rec.get('company_name', 'N/A')}")
        c.drawString(50, 690, f"ATS Match Score: {roadmap_rec.get('ats_score', 'N/A')}")
        c.drawString(50, 670, f"Generated On: {roadmap_rec.get('created_at')}")
        c.drawString(50, 650, f"Version: {roadmap_rec.get('roadmap_version', 1)}")
        
        y = 610
        r_json = json.loads(roadmap_rec['roadmap_json']) if isinstance(roadmap_rec['roadmap_json'], str) else roadmap_rec['roadmap_json']
        
        for week in ['week_1', 'week_2', 'week_3', 'week_4']:
            if week in r_json and y > 50:
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, y, r_json[week].get('title', week))
                y -= 20
                c.setFont("Helvetica", 11)
                
                topics = ", ".join(r_json[week].get('topics', []))
                if topics:
                    c.drawString(60, y, f"Topics: {topics}")
                    y -= 15
                    
                c.drawString(60, y, f"Exercise: {r_json[week].get('practical_exercise', '')}")
                y -= 30
                
        c.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"roadmap_v{roadmap_rec.get('roadmap_version', 1)}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to generate PDF"}), 500
    finally:
        conn.close()
""")
    print("Done")

if __name__ == '__main__':
    append_endpoints()
