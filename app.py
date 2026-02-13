from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import time
import json
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# --------------------------------------------------
# Load Environment Variables
# --------------------------------------------------
load_dotenv()

CONTENT_FILE = "content.json"
COLLEGE_INFO_FILE = "college_info.json"
CHATBOT_KB_FILE = "chatbot_kb.json"

# Default credentials (will be hashed)
# Ideally, you should generate a hash offline and store only the hash in env
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_RAW = os.getenv("ADMIN_PASSWORD", "National@2026Secure")
# Generate hash for the password (in a real prod app, store the HASH in env, not raw)
ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD_RAW)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-change-this-in-production")
CORS(app)

# PWA Routes
from flask import send_from_directory

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'fast_manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'images/logo.png')

# --------------------------------------------------
# Auth Decorator
# --------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            # If it's an API call, return 401
            if request.path.startswith('/api/') and request.method in ['POST', 'DELETE', 'PUT']:
                # Allow public form submissions
                if request.endpoint in ['submit_form', 'register_event']:
                    return f(*args, **kwargs)
                return jsonify({"error": "Unauthorized"}), 401
            # If it's a page load, redirect to login
            if not request.path.startswith('/api/'):
                 return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --------------------------------------------------
# Load Data
# --------------------------------------------------
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

college_info = load_json(COLLEGE_INFO_FILE)
chatbot_kb = load_json(CHATBOT_KB_FILE)

# --------------------------------------------------
# Gemini Setup
# --------------------------------------------------
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Optional: Log warning instead of crashing if key missing during dev
    print("❌ GEMINI_API_KEY not found in .env file")

client = None
if api_key:
    client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-1.5-flash"

COLLEGE_WEBSITE = "https://nationalcollege.ac.in/"
website_cache = {"data": "", "last_updated": 0}
CACHE_DURATION = 300

def scrape_website():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(COLLEGE_WEBSITE, headers=headers, timeout=6)
        if response.status_code != 200: return "Website currently unavailable."
        soup = BeautifulSoup(response.text, "lxml")
        for script in soup(["script", "style"]): script.decompose()
        text = soup.get_text(separator=" ")
        return " ".join(text.split())[:8000]
    except Exception as e:
        print("Scraping Error:", e)
        return "Unable to fetch latest website data."

def get_website_data():
    current_time = time.time()
    if current_time - website_cache["last_updated"] > CACHE_DURATION:
        website_cache["data"] = scrape_website()
        website_cache["last_updated"] = current_time
    return website_cache["data"]

# --------------------------------------------------
# System Instruction
# --------------------------------------------------
SYSTEM_INSTRUCTION = f"""
You are the official AI Assistant of {college_info.get('college_name', 'National College, Bagepalli')}.
The college was established in July 1978 and is managed by the National Education Society of Karnataka (NES).

Use both:
- Provided structured college information
- Real-time scraped website data

Rules:
- Keep answers short (3-5 lines).
- Use <strong> for bold text.
- Be professional and helpful.
- Never mention Gemini.
"""

# --------------------------------------------------
# Fast Predefined Replies
# --------------------------------------------------
def handle_predefined_questions(message):
    msg = message.lower()
    kb = chatbot_kb.get('knowledge_base', [])
    
    for category in kb:
        for q in category.get('questions', []):
            if any(keyword in msg for keyword in q.get('keywords', [])):
                return q.get('answer')
    return None

# --------------------------------------------------
# Page Routes
# --------------------------------------------------
@app.route("/")
def index(): return render_template("index.html")

@app.route("/about")
def about(): return render_template("about.html")

@app.route("/admission")
def admission(): return render_template("admission.html")

@app.route("/contact")
def contact(): return render_template("contact.html")

@app.route("/course")
def course(): return render_template("course.html")

@app.route("/faculty")
def faculty(): return render_template("faculty.html")

@app.route("/fest")
def fest(): return render_template("fest.html")

@app.route("/admin")
@login_required
def admin_root():
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    return render_template("dashboard.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template("login.html", error="Invalid Credentials")
    
    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# --------------------------------------------------
# Chat Endpoint
# --------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    if not client:
         return jsonify({"response": "Chatbot is currently disabled (API Key missing)."}), 503
         
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message: return jsonify({"response": "Please ask something about the college 😊"})

    quick_reply = handle_predefined_questions(user_message)
    if quick_reply: return jsonify({"response": quick_reply})

    website_data = get_website_data()
    structured_info = json.dumps(college_info, indent=2)

    prompt = f"College Info: {structured_info}\nWebsite Data: {website_data}\nUser Question: {user_message}"

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.5,
                max_output_tokens=500
            ),
        )
        return jsonify({"response": response.text if response.text else "Please contact the office."})
    except Exception as e:
        print("Error:", e)
        return jsonify({"response": "🤖 Scaling issues! Please try again later."}), 500

# --------------------------------------------------
# CMS & Form API
# --------------------------------------------------
@app.route("/api/content", methods=["GET"])
def get_content():
    try:
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/content", methods=["POST"])
@login_required
def update_content():
    try:
        data = request.json
        with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

SUBMISSIONS_FILE = "submissions.json"
ADMISSIONS_FILE = "admissions.json"
REGISTRATIONS_FILE = "registrations.json"

@app.route("/api/submit-form", methods=["POST"])
def submit_form():
    try:
        data = request.json
        data['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
        data['status'] = "Pending"
        form_type = data.get('form_type', 'contact')
        target_file = ADMISSIONS_FILE if form_type == 'admission' else SUBMISSIONS_FILE
        
        submissions = []
        if os.path.exists(target_file):
            with open(target_file, 'r', encoding='utf-8') as f:
                submissions = json.load(f)
        submissions.append(data)
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(submissions, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/register-event", methods=["POST"])
def register_event():
    try:
        data = request.json
        data['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
        regs = []
        if os.path.exists(REGISTRATIONS_FILE):
            with open(REGISTRATIONS_FILE, 'r', encoding='utf-8') as f:
                regs = json.load(f)
        regs.append(data)
        with open(REGISTRATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(regs, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/submissions", methods=["GET"])
@login_required
def get_submissions():
    form_type = request.args.get('type', 'contact')
    target_file = SUBMISSIONS_FILE
    if form_type == 'admission': target_file = ADMISSIONS_FILE
    elif form_type == 'registration': target_file = REGISTRATIONS_FILE
    if not os.path.exists(target_file): return jsonify([])
    with open(target_file, 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))

@app.route("/api/export/<category>", methods=["GET"])
@login_required
def export_csv(category):
    import io, csv
    from flask import make_response
    target_file = {"admissions": ADMISSIONS_FILE, "registrations": REGISTRATIONS_FILE, "contact": SUBMISSIONS_FILE}.get(category)
    if not target_file or not os.path.exists(target_file): return "No data", 404
    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data: return "No data", 404
    keys = sorted(list(set().union(*(d.keys() for d in data))))
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    writer.writerows(data)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={category}.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response

@app.route("/api/submissions/status", methods=["POST"])
@login_required
def update_status():
    data = request.json
    index, new_status, form_type = data.get('index'), data.get('status'), data.get('form_type', 'contact')
    target_file = ADMISSIONS_FILE if form_type == 'admission' else SUBMISSIONS_FILE
    with open(target_file, 'r', encoding='utf-8') as f:
        submissions = json.load(f)
    submissions[index]['status'] = new_status
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(submissions, f, indent=2, ensure_ascii=False)
    return jsonify({"status": "success"})

@app.route("/api/submissions", methods=["POST"])
@login_required
def delete_submission():
    data = request.json
    index, form_type = data.get('index'), data.get('form_type', 'contact')
    target_file = {"admission": ADMISSIONS_FILE, "registration": REGISTRATIONS_FILE}.get(form_type, SUBMISSIONS_FILE)
    if not os.path.exists(target_file): return jsonify({"status": "error"}), 404
    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if index < len(data):
        data.pop(index)
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)

