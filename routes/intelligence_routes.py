import hashlib
import json
import logging
import time
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import get_db_connection
from utils.ats_engine import generate_resume_hash, calculate_career_intelligence_score
from utils.ats_engine import generate_resume_hash, calculate_career_intelligence_score

intelligence_bp = Blueprint('intelligence', __name__)

@intelligence_bp.route('/api/intelligence/gap-analysis', methods=['POST'])
@jwt_required()
def analyze_gap():
    import time
    from utils.telemetry import increment_metric, record_latency
    start_time = time.time()
    
    user_id = get_jwt_identity()
    data = request.json
    
    resume_id = data.get("resume_id")
    jd_text = data.get("jd_text")
    
    if not resume_id or not jd_text:
        return jsonify({"error": "Missing resume_id or jd_text"}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Fallback Logic for Resume Text
            cursor.execute("SELECT resume_text, user_id FROM resumes WHERE resume_id = %s AND is_active = 1", (resume_id,))
            resume = cursor.fetchone()
            
            if not resume:
                return jsonify({"error": "Resume not found"}), 404
                
            if str(resume['user_id']) != str(user_id):
                return jsonify({"error": "Unauthorized"}), 403
                
            cursor.execute("SELECT optimized_resume_text FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone()
            
            if profile and profile.get('optimized_resume_text'):
                resume_text = profile['optimized_resume_text']
            else:
                resume_text = resume['resume_text']
                
            # 2. Check Cache
            resume_hash = generate_resume_hash(resume_text)
            jd_hash = generate_resume_hash(jd_text) # Reusing hash function
            cache_key = f"{user_id}_{resume_hash}_{jd_hash}"
            
            cursor.execute("SELECT * FROM intelligence_cache WHERE cache_key = %s AND generated_at >= NOW() - INTERVAL 24 HOUR", (cache_key,))
            cache_entry = cursor.fetchone()
            
            if cache_entry:
                logging.info(f"INTELLIGENCE_CACHE_HIT user={user_id}")
                increment_metric("intel_cache_hits")
                record_latency("gap_analysis", int((time.time() - start_time) * 1000))
                return jsonify({
                    "readiness_score": cache_entry['readiness_score'],
                    "intelligence_score": cache_entry['intelligence_score'],
                    "gap_analysis": json.loads(cache_entry['skill_gap_json']),
                    "roadmap": json.loads(cache_entry['roadmap_json']) if cache_entry['roadmap_json'] else None
                })
                
            logging.info(f"INTELLIGENCE_CACHE_MISS user={user_id}")
            increment_metric("intel_cache_misses")
            
            # 3. Call JDAnalyzerService instead of Gemini
            from jd_analyzer.services.jd_analyzer import JDAnalyzerService
            analyzer = JDAnalyzerService()
            raw_analysis = analyzer.analyze(jd_text=jd_text, resume_text=resume_text)
            
            scores = raw_analysis.get('scores', {})
            skill_gap = raw_analysis.get('skill_gap', {})
            jd_skills = raw_analysis.get('jd_skills', {}).get('all', [])
            
            missing_skills = [obj.get('skill') for obj in skill_gap.get('missing', [])]
            priority_skills = missing_skills[:5] if missing_skills else jd_skills[:5]
            
            readiness_score = int(scores.get('overall_score', 0))
            
            job_title = raw_analysis.get('jd_entities', {}).get('job_title', 'Target Role')
            company = raw_analysis.get('jd_entities', {}).get('company', 'Target Company')
            
            from jd_analyzer.services.recommendation_engine import RecommendationEngine
            engine = RecommendationEngine()
            
            project_recs = engine.generate_project_recommendations(job_title, missing_skills, jd_skills)
            interview_prep = engine.generate_interview_prep(missing_skills, jd_skills)
            experience_recs = engine.generate_experience_improvements(job_title, missing_skills)
            
            gap_data = {
                "readiness_score": readiness_score,
                "project_gaps": project_recs,
                "interview_topics": interview_prep,
                "priority_skills": priority_skills,
                "critical_risks": experience_recs.get("missing_evidence", [])
            }
                
            # Calculate deterministic Career Intelligence Score
            intelligence_score = calculate_career_intelligence_score(resume_text, jd_text, readiness_score)
            
            # Store in cache (upsert)
            cursor.execute("""
                INSERT INTO intelligence_cache 
                (cache_key, user_id, resume_hash, jd_hash, readiness_score, intelligence_score, skill_gap_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                readiness_score=VALUES(readiness_score),
                intelligence_score=VALUES(intelligence_score),
                skill_gap_json=VALUES(skill_gap_json),
                generated_at=CURRENT_TIMESTAMP
            """, (cache_key, user_id, resume_hash, jd_hash, readiness_score, intelligence_score, json.dumps(gap_data)))
            
            conn.commit()
            
            return jsonify({
                "readiness_score": readiness_score,
                "intelligence_score": intelligence_score,
                "gap_analysis": gap_data,
                "roadmap": None
            })
            
    except Exception as e:
        logging.error(f"Gap Analysis Error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()


@intelligence_bp.route('/api/intelligence/roadmap', methods=['POST'])
@jwt_required()
def generate_roadmap():
    user_id = get_jwt_identity()
    data = request.json
    
    priority_skills = data.get("priority_skills")
    resume_id = data.get("resume_id")
    jd_id = data.get("jd_id")
    jd_text = data.get("jd_text")
    force_regenerate = data.get("force_regenerate", False)
    
    if not priority_skills or not resume_id or not jd_text or not jd_id:
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Get Resume Text
            cursor.execute("SELECT resume_text FROM resumes WHERE resume_id = %s AND user_id = %s AND is_active = 1", (resume_id, user_id))
            resume = cursor.fetchone()
            if not resume:
                return jsonify({"error": "Resume not found"}), 404
                
            cursor.execute("SELECT optimized_resume_text FROM builder_profiles WHERE user_id = %s", (user_id,))
            profile = cursor.fetchone()
            
            if profile and profile.get('optimized_resume_text'):
                resume_text = profile['optimized_resume_text']
            else:
                resume_text = resume['resume_text']
                
            resume_hash = generate_resume_hash(resume_text)
            jd_hash = generate_resume_hash(jd_text)
            
            # 4. Get historical scores & missing context
            cursor.execute("SELECT ats_score, title FROM job_descriptions WHERE id = %s", (jd_id,))
            jd_rec = cursor.fetchone()
            ats_score = jd_rec['ats_score'] if jd_rec else 0
            job_title = jd_rec['title'] if jd_rec else "Target Role"
            
            cache_key = f"{user_id}_{resume_hash}_{jd_hash}"
            cursor.execute("SELECT intelligence_score, readiness_score, skill_gap_json FROM intelligence_cache WHERE cache_key = %s", (cache_key,))
            intel_rec = cursor.fetchone()
            match_score = intel_rec['intelligence_score'] if intel_rec else 0
            readiness_score = intel_rec['readiness_score'] if intel_rec else 0
            
            project_gaps = []
            interview_topics = []
            if intel_rec and intel_rec['skill_gap_json']:
                try:
                    sg_json = json.loads(intel_rec['skill_gap_json']) if isinstance(intel_rec['skill_gap_json'], str) else intel_rec['skill_gap_json']
                    project_gaps = sg_json.get('project_gaps', [])
                    interview_topics = sg_json.get('interview_topics', [])
                except Exception:
                    pass
            
            # 2. Check if a roadmap already exists for these hashes
            if not force_regenerate:
                cursor.execute("""
                    SELECT id, roadmap_json FROM roadmaps 
                    WHERE user_id = %s AND jd_id = %s AND resume_hash = %s AND jd_hash = %s
                    ORDER BY id DESC LIMIT 1
                """, (user_id, jd_id, resume_hash, jd_hash))
                existing_roadmap = cursor.fetchone()
                
                if existing_roadmap and existing_roadmap.get('roadmap_json'):
                    logging.info(f"ROADMAP_DB_HIT user={user_id}")
                    return jsonify({"roadmap_id": existing_roadmap['id'], "roadmap": json.loads(existing_roadmap['roadmap_json'])})
                    
            logging.info(f"ROADMAP_DB_MISS user={user_id}")
            
            # 3. Generate new roadmap using JDAnalyzerService logic
            from jd_analyzer.services.jd_analyzer import JDAnalyzerService
            from jd_analyzer.services.recommendation_engine import RecommendationEngine
            
            analyzer = JDAnalyzerService()
            engine = RecommendationEngine()
            
            raw_analysis = analyzer.analyze(jd_text=jd_text, resume_text=resume_text)
            
            job_title = raw_analysis.get('jd_entities', {}).get('job_title', 'Target Role')
            company_name = raw_analysis.get('jd_entities', {}).get('company', 'Target Company')
            employment_type = raw_analysis.get('jd_entities', {}).get('employment_type', 'Unknown')
            
            jd_skills = raw_analysis.get('jd_skills', {}).get('all', [])
            skill_gap = raw_analysis.get('skill_gap', {})
            missing_skills = [obj.get('skill') for obj in skill_gap.get('missing', [])]
            
            phases = engine.generate_roadmap_phases(job_title, company_name, missing_skills, jd_skills)
            project_gaps = engine.generate_project_recommendations(job_title, missing_skills, jd_skills)
            interview_topics = engine.generate_interview_prep(missing_skills, jd_skills)
                
            roadmap_data = {
                "target_company": company_name,
                "phases": phases
            }
                
            # 4. Get historical scores
            cursor.execute("SELECT ats_score FROM job_descriptions WHERE id = %s", (jd_id,))
            jd_rec = cursor.fetchone()
            ats_score = jd_rec['ats_score'] if jd_rec else 0
            
            cache_key = f"{user_id}_{resume_hash}_{jd_hash}"
            cursor.execute("SELECT intelligence_score FROM intelligence_cache WHERE cache_key = %s", (cache_key,))
            intel_rec = cursor.fetchone()
            match_score = intel_rec['intelligence_score'] if intel_rec else 0
            
            # Get max version
            cursor.execute("SELECT MAX(roadmap_version) as max_v FROM roadmaps WHERE jd_id = %s AND user_id = %s", (jd_id, user_id))
            v_rec = cursor.fetchone()
            next_version = (v_rec['max_v'] or 0) + 1
            
            company_name = roadmap_data.get('target_company', 'Target Company')
            
            # Save to roadmaps table
            cursor.execute("""
                INSERT INTO roadmaps (user_id, jd_id, company_name, job_title, roadmap_json, ats_score, match_score, resume_hash, jd_hash, roadmap_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, jd_id, company_name, job_title, json.dumps(roadmap_data), ats_score, match_score, resume_hash, jd_hash, next_version))
            
            roadmap_id = cursor.lastrowid
            
            # Save to roadmap_progress and roadmap_phases table
            phases = roadmap_data.get('phases', [])
            for idx, p in enumerate(phases, start=1):
                phase_name = p.get('phase', 'Phase')
                
                # roadmap_progress (legacy)
                cursor.execute("""
                    INSERT INTO roadmap_progress (roadmap_id, phase_name, status, completion_percentage)
                    VALUES (%s, %s, 'NOT_STARTED', 0)
                """, (roadmap_id, phase_name))
                
                # roadmap_phases (new)
                try:
                    duration_str = p.get('duration', '1 Week')
                    weeks = int(duration_str.split()[0]) if duration_str.split()[0].isdigit() else 1
                    
                    cursor.execute("""
                        INSERT INTO roadmap_phases 
                        (roadmap_id, phase_number, title, duration_weeks, objectives, activities, deliverables, success_criteria)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        roadmap_id, idx, phase_name, weeks,
                        json.dumps(p.get('objectives', [])),
                        json.dumps(p.get('activities', [])),
                        json.dumps(p.get('deliverables', [])),
                        json.dumps(p.get('success_criteria', ''))
                    ))
                    phase_id = cursor.lastrowid
                    
                    # user_roadmap_progress (new)
                    cursor.execute("""
                        INSERT INTO user_roadmap_progress (user_id, roadmap_id, phase_id, status)
                        VALUES (%s, %s, %s, 'NOT_STARTED')
                    """, (user_id, roadmap_id, phase_id))
                except Exception as e:
                    logging.error(f"Failed inserting into roadmap_phases: {e}")
            
            # Physical PDF saving
            pdf_path = create_physical_pdf(roadmap_id, user_id, cursor, roadmap_data, job_title, company_name, employment_type, ats_score, readiness_score, priority_skills, project_gaps, interview_topics)
            if pdf_path:
                cursor.execute("UPDATE roadmaps SET pdf_path = %s WHERE id = %s", (pdf_path, roadmap_id))
            
            # Update cache for compatibility
            cursor.execute("UPDATE intelligence_cache SET roadmap_json = %s WHERE cache_key = %s", (json.dumps(roadmap_data), cache_key))
            conn.commit()
            
            return jsonify({"roadmap_id": roadmap_id, "roadmap": roadmap_data})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f"Roadmap Error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

def create_physical_pdf(roadmap_id, user_id, cursor, roadmap_data, job_title, company_name, employment_type, ats_score, readiness_score, missing_skills, project_gaps, interview_topics):
    try:
        cursor.execute("SELECT name FROM students WHERE id = %s", (user_id,))
        student_rec = cursor.fetchone()
        student_name = student_rec['name'] if student_rec else "Student"
        
        import re
        
        display_role = job_title if job_title and job_title.lower() not in ['role', 'target role', 'role not clearly specified'] else "Not Clearly Mentioned"
        if ", you will" in display_role.lower():
            # Sometimes LLM includes ", you will be responsible for..."
            idx = display_role.lower().find(", you will")
            display_role = display_role[:idx].strip()
            
        safe_company = re.sub(r'[^a-zA-Z0-9]', '', company_name.split()[0] if company_name else 'Company')
        safe_role = re.sub(r'[^a-zA-Z0-9]', '_', display_role)
        if not safe_role or safe_role.lower() == 'not_clearly_mentioned':
            safe_role = 'Role'
        
        os.makedirs("static/roadmaps", exist_ok=True)
        file_path = f"static/roadmaps/{safe_company}_{safe_role}_Roadmap.pdf"
        
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        
        # Base styles
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=16.5,
            spaceAfter=6
        )
        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=normal_style,
            leftIndent=15,
            firstLineIndent=-15
        )
        h1_style = ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=16,
            leading=24,
            spaceAfter=12
        )
        h2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=14,
            leading=21,
            spaceAfter=10,
            spaceBefore=15,
            textColor='#1a1a1a'
        )
        h3_style = ParagraphStyle(
            'CustomH3',
            parent=styles['Heading3'],
            fontSize=12,
            leading=18,
            spaceAfter=6,
            spaceBefore=10
        )
        
        story = []
        
        story.append(Paragraph("Professional Career Learning Roadmap", h1_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Profile Section
        story.append(Paragraph("Student Profile", h2_style))
        story.append(Paragraph(f"<b>Name:</b> {student_name}", normal_style))
        story.append(Paragraph(f"<b>Target Company:</b> {company_name}", normal_style))
        story.append(Paragraph(f"<b>Target Role:</b> {display_role}", normal_style))
        if employment_type and employment_type != 'Unknown':
            story.append(Paragraph(f"<b>Employment Type:</b> {employment_type}", normal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Metrics removed per request
        
        # Gap Analysis
        def filter_ats_metrics(items):
            if not items: return []
            ats_keywords = ['formatting', 'readability', 'grammar', 'syntax', 'clarity', 'resume structure', 'null', 'none']
            return [x for x in items if str(x).strip() and not any(kw in str(x).lower() for kw in ats_keywords)]
        
        f_missing_skills = filter_ats_metrics(missing_skills)
        f_project_gaps = filter_ats_metrics(project_gaps)
        f_interview_topics = filter_ats_metrics(interview_topics)
        
        if f_missing_skills or f_project_gaps or f_interview_topics:
            story.append(Paragraph("Gap Analysis & Recommendations", h2_style))
            
            if f_missing_skills:
                story.append(Paragraph("<b>Key Skill Gaps:</b>", h3_style))
                skills_list = [ListItem(Paragraph(str(sk), normal_style)) for sk in f_missing_skills]
                story.append(ListFlowable(skills_list, bulletType='bullet', leftIndent=10))
                
            if f_project_gaps:
                story.append(Paragraph("<b>Recommended Projects:</b>", h3_style))
                has_str = False
                projects_list = []
                for pg in f_project_gaps:
                    if isinstance(pg, dict):
                        title = pg.get('title', 'Project')
                        desc = pg.get('description', '')
                        feats = pg.get('features', [])
                        diff = pg.get('difficulty', 'Intermediate')
                        pval = pg.get('portfolio_value', 'High')
                        
                        story.append(Paragraph(f"<b>Project:</b> {title}", ParagraphStyle('Sub', parent=normal_style, spaceAfter=2, spaceBefore=4)))
                        story.append(Paragraph(f"<b>Description:</b> {desc}", ParagraphStyle('P', parent=normal_style, leftIndent=10, spaceAfter=2)))
                        if feats:
                            story.append(Paragraph("<b>Features:</b>", ParagraphStyle('P', parent=normal_style, leftIndent=10, spaceAfter=2)))
                            for feat in feats:
                                story.append(Paragraph(f"- {feat}", ParagraphStyle('F', parent=normal_style, leftIndent=20, spaceAfter=1)))
                        story.append(Paragraph(f"<b>Difficulty:</b> {diff}", ParagraphStyle('P', parent=normal_style, leftIndent=10, spaceAfter=2)))
                        story.append(Paragraph(f"<b>Portfolio Value:</b> {pval}", ParagraphStyle('P', parent=normal_style, leftIndent=10, spaceAfter=4)))
                        story.append(Spacer(1, 0.1*inch))
                    else:
                        has_str = True
                        projects_list.append(ListItem(Paragraph(str(pg), normal_style)))
                if has_str:
                    story.append(ListFlowable(projects_list, bulletType='bullet', leftIndent=10))
                
            if f_interview_topics:
                story.append(Paragraph("<b>Interview Preparation:</b>", h3_style))
                has_str = False
                topics_list = []
                for it in f_interview_topics:
                    if isinstance(it, dict):
                        cat = it.get('category', 'Topic')
                        qs = it.get('questions', [])
                        
                        story.append(Paragraph(f"<b>{cat} Preparation</b>", ParagraphStyle('Sub', parent=normal_style, spaceAfter=2, spaceBefore=4)))
                        
                        if qs:
                            story.append(Paragraph("<i>Questions:</i>", ParagraphStyle('SubSub', parent=normal_style, spaceAfter=2, leftIndent=10)))
                            for idx, q in enumerate(qs[:3]):
                                story.append(Paragraph(f"{idx+1}. {q.get('question', '')}", ParagraphStyle('Q', parent=normal_style, leftIndent=20, spaceAfter=2)))
                        
                        vids = it.get('videos', [])
                        if vids:
                            story.append(Paragraph("<i>Resources:</i>", ParagraphStyle('SubSub', parent=normal_style, spaceAfter=2, spaceBefore=4, leftIndent=10)))
                            for v in vids[:2]:
                                story.append(Paragraph(f"{v.get('channel', 'Channel')}<br/><font color='blue'><u><a href='{v.get('url', '#')}'>{v.get('url', '#')}</a></u></font>", ParagraphStyle('V', parent=normal_style, leftIndent=20, spaceAfter=4)))
                            
                        story.append(Spacer(1, 0.1*inch))
                    else:
                        has_str = True
                        topics_list.append(ListItem(Paragraph(str(it), normal_style)))
                
                if has_str:
                    story.append(ListFlowable(topics_list, bulletType='bullet', leftIndent=10))
                
            story.append(Spacer(1, 0.3*inch))
            
        # Phases
        phases = roadmap_data.get('phases', [])
        for phase in phases:
            phase_story = []
            phase_title = str(phase.get('phase', 'Phase'))
            phase_story.append(Paragraph(phase_title, h2_style))
            
            def add_list_section(title, items):
                if items:
                    if isinstance(items, str):
                        items = [items]
                    phase_story.append(Paragraph(f"<b>{title}:</b>", normal_style))
                    bulleted_items = [ListItem(Paragraph(str(item), normal_style)) for item in items if str(item).strip()]
                    if bulleted_items:
                        phase_story.append(ListFlowable(bulleted_items, bulletType='bullet', leftIndent=10))
                        phase_story.append(Spacer(1, 4))
            
            duration = phase.get('duration')
            if duration:
                phase_story.append(Paragraph(f"<b>Duration:</b> {duration}", normal_style))
                phase_story.append(Spacer(1, 4))
                
            add_list_section("Objectives", phase.get('objectives', []))
            add_list_section("Activities", phase.get('activities', []))
            add_list_section("Deliverables", phase.get('deliverables', []))
            
            success = phase.get('success_criteria')
            if success:
                phase_story.append(Paragraph(f"<b>Success Criteria:</b> {success}", normal_style))
                
            outcome = phase.get('expected_outcome')
            if outcome:
                add_list_section("Expected Outcome", outcome)
                
            phase_story.append(Spacer(1, 0.2*inch))
            
            # Keep phases intact
            story.append(KeepTogether(phase_story))
            
        doc.build(story)
        return file_path
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f"Error creating PDF: {e}")
        return None


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
            cursor.execute("SELECT company_name, job_title, pdf_path, roadmap_version FROM roadmaps WHERE id = %s AND user_id = %s", (roadmap_id, user_id))
            roadmap_rec = cursor.fetchone()
            
            if not roadmap_rec:
                return jsonify({"error": "Roadmap not found"}), 404
                
        from flask import send_file
        import re
        
        pdf_path = roadmap_rec.get('pdf_path')
        if pdf_path and os.path.exists(pdf_path):
            company = roadmap_rec.get('company_name', 'Company')
            if not company or company == 'Target Company': company = 'Company'
            role = roadmap_rec.get('job_title', 'Role')
            if not role or role == 'Target Role' or role == 'Role not clearly specified': role = ''
            
            clean_company = re.sub(r'[^A-Za-z0-9]', '', company)
            display_role = role
            if ", you will" in display_role.lower():
                idx = display_role.lower().find(", you will")
                display_role = display_role[:idx].strip()
            clean_role = re.sub(r'[^A-Za-z0-9]', '_', display_role)
            
            if clean_role:
                dl_name = f"{clean_company}_{clean_role}_Roadmap.pdf"
            else:
                dl_name = f"{clean_company}_Roadmap.pdf"
                
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=dl_name,
                mimetype='application/pdf'
            )
        else:
            return jsonify({"error": "PDF file not found on server"}), 404
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to serve PDF"}), 500
    finally:
        conn.close()
