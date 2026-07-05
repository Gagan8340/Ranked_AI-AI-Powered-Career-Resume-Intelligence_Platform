# Ranked.ai - AI-Powered Career & Resume Platform 🎓🚀

Ranked.ai is a comprehensive **AI-Powered Career & Resume Platform** built with Python, Flask, and Google's Gemini AI. It is designed to bridge the gap between candidate resumes and industry job descriptions using advanced Natural Language Processing (NLP), deterministic ATS simulation, and generative AI.

---

## ✨ Features & Functionality

### 1. 🤖 Deterministic ATS Engine (`ats_score_checker`)
Simulates how enterprise Applicant Tracking Systems (ATS) parse resumes to generate a precise "ATS Compatibility Score".
*   **Parsing Pipeline:** Uses `PyMuPDF` (for PDFs), `python-docx` (for Word), and `pytesseract` (for OCR on images) to extract text precisely.
*   **Structural Analysis:** Uses regex pattern matching to detect core resume sections (Experience, Education, Skills) and checks for ATS-hostile formatting (e.g., complex tables, multi-column layouts).
*   **Readability & Syntax Scoring:** Computes a readability index and checks for action-verb density.

### 2. 🎯 Job Description (JD) Analyzer & Semantic Matcher
Deeply parses Job Descriptions to extract core requirements and cross-references them against your resume.
*   **Semantic Matching Algorithm:** Uses `sentence-transformers` (`all-MiniLM-L6-v2`) and `torch` to generate text embeddings, calculating the exact cosine similarity between the JD and the resume.
*   **Skill Extraction:** Uses `spaCy` NLP pipelines to extract specific technical skills and soft skills.
*   **Skill Gap Analysis:** Highlights exact matching skills and identifies critical missing skills from your resume.

### 3. 📄 LaTeX Resume Builder
*   **Dynamic Builder:** Create, edit, and format professional, ATS-friendly resumes directly within the platform.
*   **LaTeX Compilation:** Uses Jinja2 templating to dynamically generate LaTeX code from user data, which is then compiled into a highly professional, perfectly formatted PDF.

### 4. ⚡ Generative AI Resume Optimizer
*   **Context-Aware Tailoring:** Leverages Google's **Gemini AI** (`google-genai`) to automatically rewrite and optimize resume bullets, perfectly aligning phrasing with a target Job Description while maintaining factual accuracy.

### 5. ✍️ Smart Cover Letter Generator
*   **1-Click Generation:** Auto-generates personalized, highly-tailored cover letters using Gemini, mapping the user's parsed resume directly to the target JD's requirements.

### 6. 📊 User Dashboard
*   **Activity Tracking:** Tracks historical ATS scores and improvements over time using dynamic charts.
*   **Resume Management:** Maintain and analyze multiple versions of resumes.

### 7. 🔒 Security & Authentication
*   **JWT Authentication:** Utilizes `Flask-JWT-Extended` with dual `HttpOnly` cookies and Bearer tokens for API security.
*   **Role-Based Access:** Dedicated routes for standard users, admins, and recruiters.
*   **Password Hashing:** Uses `bcrypt` for secure password storage.

---

## 🛠️ Tech Stack & Requirements

*   **Backend:** Python 3.10+, Flask, Werkzeug
*   **Database:** MySQL (using `PyMySQL`)
*   **AI/ML:** Google Gemini API, `sentence-transformers`, `torch`, `scikit-learn`, `spaCy`
*   **PDF/Document Processing:** `PyMuPDF`, `python-docx`, `pytesseract`, `weasyprint`
*   **Frontend:** HTML5, Vanilla CSS (Custom Design System), JavaScript, Chart.js, Lucide Icons

---

## 🚀 Setup & Installation (Local Development)

### 1. System Prerequisites
*   **Python 3.10+**
*   **MySQL Server** (Local or Cloud)
*   **Tesseract OCR** (Must be installed on your OS and added to PATH for image parsing)

### 2. Install Dependencies

Clone the repository and set up a virtual environment:

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # On Windows
# source venv/bin/activate # On Mac/Linux

# Install all required Python packages
pip install -r requirements.txt
```

*(Note: The `sentence-transformers` and `torch` packages may take a few minutes to download).* 

### 3. Environment Variables
Create a `.env` file in the root directory and configure the following required variables:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ai_career_platform
DB_USER=root
DB_PASSWORD=your_password

# Authentication & Security
JWT_SECRET_KEY=your_super_secret_jwt_key_min_64_chars
JWT_ACCESS_TOKEN_EXPIRES_HOURS=24
JWT_COOKIE_SECURE=False # Set to True in Production (HTTPS)
FORCE_HTTPS=False

# AI Integration
GEMINI_API_KEY=your_google_gemini_api_key

# Upload Constraints
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=static/uploads
```

### 4. Run the Application
The `init_db()` function in `config.py` will automatically create the required MySQL database tables on the first run. Ensure your MySQL server is running before executing.

```powershell
python app.py
```

The application will be accessible at `http://127.0.0.1:5000`.

---

## ☁️ Production Deployment

1.  **Database:** Provision a production MySQL instance.
2.  **Environment:** Inject all `.env` values into your production environment variables. Ensure `JWT_COOKIE_SECURE=True` and `FORCE_HTTPS=True`.
3.  **Start Command:** Run the app using a production WSGI server like Gunicorn (Waitress for Windows):
    ```bash
    pip install gunicorn
gunicorn "app:create_app()" --bind 0.0.0.0:5000
    ```
