"""
JD Analyzer Flask Blueprint
All routes are prefixed with /jd-analyzer/.

Integration into main Flask app:
    from jd_analyzer.routes import jd_analyzer_bp
    app.register_blueprint(jd_analyzer_bp)
"""

import logging
import traceback
from flask import (
    Blueprint,
    request,
    render_template,
    jsonify,
    current_app,
    session,
)
from werkzeug.utils import secure_filename
from .services import JDAnalyzerService

logger = logging.getLogger(__name__)

jd_analyzer_bp = Blueprint(
    "jd_analyzer",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/jd-analyzer/static",
    url_prefix="/jd-analyzer",
)

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}
# Max upload size (16 MB)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024


def _allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _get_service() -> JDAnalyzerService:
    """Get or create the singleton JDAnalyzerService on the app context."""
    if not hasattr(current_app, "_jd_analyzer_service"):
        current_app._jd_analyzer_service = JDAnalyzerService()
    return current_app._jd_analyzer_service


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@jd_analyzer_bp.route("/", methods=["GET"])
def index():
    """Main JD Analyzer page."""
    return render_template("jd_analyzer/index.html")


@jd_analyzer_bp.route("/analyze", methods=["POST"])
def analyze():
    """
    POST endpoint for JD analysis.

    Form fields:
        jd_input_type: "file" | "text"
        jd_file: (file upload, if type=file)
        jd_text: (textarea text, if type=text)
        resume_input_type: "file" | "text" | "none"
        resume_file: (file upload, if type=file)
        resume_text: (textarea text, if type=text)

    Returns: JSON analysis report.
    """
    try:
        service = _get_service()

        # ---- JD Input ----
        jd_input_type = request.form.get("jd_input_type", "text")
        jd_file = None
        jd_filename = ""
        jd_text = ""

        if jd_input_type == "file":
            if "jd_file" not in request.files:
                return jsonify({"status": "error", "message": "No JD file uploaded."}), 400
            file = request.files["jd_file"]
            if not file.filename:
                return jsonify({"status": "error", "message": "Empty filename."}), 400
            if not _allowed_file(file.filename):
                return jsonify({
                    "status": "error",
                    "message": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                }), 400
            jd_file = file
            jd_filename = secure_filename(file.filename)
        else:
            jd_text = request.form.get("jd_text", "").strip()
            if not jd_text:
                return jsonify({"status": "error", "message": "No JD text provided."}), 400
            if len(jd_text) < 50:
                return jsonify({
                    "status": "error",
                    "message": "JD text is too short. Please provide a complete job description."
                }), 400

        # ---- Resume Input (optional) ----
        resume_input_type = request.form.get("resume_input_type", "none")
        resume_file = None
        resume_filename = ""
        resume_text = ""

        if resume_input_type == "file":
            if "resume_file" in request.files:
                rfile = request.files["resume_file"]
                if rfile.filename and _allowed_file(rfile.filename):
                    resume_file = rfile
                    resume_filename = secure_filename(rfile.filename)
        elif resume_input_type == "text":
            resume_text = request.form.get("resume_text", "").strip()

        # ---- Run Analysis ----
        result = service.analyze(
            jd_file=jd_file,
            jd_filename=jd_filename,
            jd_text=jd_text,
            resume_file=resume_file,
            resume_filename=resume_filename,
            resume_text=resume_text,
        )

        return jsonify(result)

    except ValueError as e:
        logger.warning(f"[JDAnalyzer] Validation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except RuntimeError as e:
        logger.error(f"[JDAnalyzer] Runtime error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 422
    except Exception as e:
        logger.error(f"[JDAnalyzer] Unexpected error: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred. Please try again."
        }), 500


@jd_analyzer_bp.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "jd_analyzer"})
