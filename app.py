from flask import Flask, render_template, request, redirect, session, url_for, flash
import pdfplumber
import os
import spacy
import psycopg2
import urllib.parse as urlparse
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# Upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load NLP model
nlp = spacy.load("en_core_web_sm")

# ---------------- DB CONNECTION ---------------- #
def get_connection():
    url = urlparse.urlparse(os.environ.get("DATABASE_URL"))

    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    return conn

# ---------------- KEYWORD EXTRACTION ---------------- #
def extract_keywords(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    words = text.split()

    stopwords = ["and", "or", "the", "with", "for", "a", "an", "to", "in"]
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    return list(set(keywords))

# ---------------- REGISTER ---------------- #
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        conn = get_connection()
        cursor = conn.cursor()

        try:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
            conn.commit()
            flash("Account created! Please login.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            conn.rollback()
            flash("Username already exists!", "danger")

        finally:
            conn.close()

    return render_template('register.html')

# ---------------- LOGIN ---------------- #
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

# ---------------- LOGOUT ---------------- #
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- MAIN ---------------- #
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    result = None

    if request.method == 'POST':
        file = request.files['resume']
        jd_text = request.form.get('jd', '')

        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            resume_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    resume_text += page.extract_text() or ""

            resume_keywords = extract_keywords(resume_text)
            jd_keywords = extract_keywords(jd_text)

            matched = list(set(resume_keywords) & set(jd_keywords))
            match_score = int((len(matched) / len(jd_keywords)) * 100) if jd_keywords else 0
            suggestions = list(set(jd_keywords) - set(resume_keywords))[:5]

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO resumes (filename, match_score, skills, user_id)
                VALUES (%s, %s, %s, %s)
            """, (file.filename, match_score, ", ".join(matched), session['user_id']))
            conn.commit()
            conn.close()

            result = {
                "match_score": match_score,
                "matched_skills": matched,
                "suggestions": suggestions
            }

    return render_template('index.html', result=result)

# ---------------- HISTORY ---------------- #
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resumes WHERE user_id=%s", (session['user_id'],))
    data = cursor.fetchall()
    conn.close()

    return render_template('history.html', data=data)

# ---------------- RUN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)