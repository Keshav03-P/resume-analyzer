from flask import Flask, render_template, request, redirect, session, url_for
import pdfplumber
import os
import spacy
import psycopg2
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.security import generate_password_hash, check_password_hash
from skills import SKILLS, SKILL_SYNONYMS

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# Upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# SpaCy model
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

# PostgreSQL Connection
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


# Create tables automatically

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id SERIAL PRIMARY KEY,
            filename TEXT,
            match_score INT,
            skills TEXT,
            user_id INT
        )
    """)

    conn.commit()
    conn.close()


create_tables()


# Extract keywords

def extract_keywords(text):
    text = text.lower()

    found_skills = []

    for skill in SKILLS:
        if skill.lower() in text:
            found_skills.append(skill)

    for synonym, real_skill in SKILL_SYNONYMS.items():
        if synonym.lower() in text:
            found_skills.append(real_skill)

    return list(set(found_skills))
    
def semantic_match(resume_text, jd_text):

    resume_embedding = model.encode([resume_text])
    jd_embedding = model.encode([jd_text])

    similarity = cosine_similarity(
        resume_embedding,
        jd_embedding
    )[0][0]

    return int(similarity * 100)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        raw_password = request.form.get('password').strip()

        hashed_password = generate_password_hash(raw_password)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed_password)
        )

        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# Main page
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect('/login')

    result = {}

    if request.method == 'POST':
        file = request.files['resume']
        jd_text = request.form.get('jd', '')

        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Extract PDF text
            resume_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    resume_text += page.extract_text() or ""

            resume_text = resume_text.lower()

            # Skill extraction
            resume_keywords = extract_keywords(resume_text)
            jd_keywords = extract_keywords(jd_text)

            matched = list(set(resume_keywords) & set(jd_keywords))

            match_score = semantic_match(
                resume_text,
                jd_text
            )

            suggestions = list(
                set(jd_keywords) - set(resume_keywords)
            )

            # AI Suggestions
            ai_tips = []

            if 'rest api' in suggestions:
                ai_tips.append('Add REST API project experience')

            if 'postgresql' in suggestions:
                ai_tips.append('Mention PostgreSQL database work')

            if 'git' in suggestions:
                ai_tips.append('Add GitHub or Git workflow experience')

            if 'testing' in suggestions:
                ai_tips.append('Include testing or debugging experience')

            # Save history
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO resumes (filename, match_score, skills, user_id)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    file.filename,
                    match_score,
                    ", ".join(matched),
                    session['user_id']
                )
            )

            conn.commit()
            conn.close()

            result = {
                'match_score': match_score,
                'matched_skills': matched,
                'suggestions': suggestions,
                'ai_tips': ai_tips
            }

    return render_template('index.html', result=result)


# History
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM resumes WHERE user_id=%s",
        (session['user_id'],)
    )

    data = cursor.fetchall()
    conn.close()

    return render_template('history.html', data=data)


if __name__ == '__main__':
    app.run(debug=True)

