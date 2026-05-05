# 📄 Resume Analyzer (AI-Based)

A Flask-based web application that analyzes resumes and compares them with job descriptions to calculate a match score and suggest missing skills.

---

## 🚀 Features

- Upload Resume (PDF)
- Paste Job Description
- Match Score Calculation (%)
- Extract Matched Skills
- Suggest Missing Skills
- User Login & Registration
- Resume History Tracking
- Charts (Score + Skills)

---

## 🛠️ Tech Stack

- Python (Flask)
- HTML + Bootstrap
- Chart.js
- NLP (spaCy)
- PostgreSQL (Render DB)
- PDF Processing (pdfplumber)

---

## 📂 Project Structure
resume-analyzer/
│
├── app.py
├── skills.py
├── requirements.txt
├── Procfile
├── init_db.py
│
├── templates/
│ ├── index.html
│ ├── login.html
│ ├── register.html
│ └── history.html


---

## ⚙️ Environment Variables

Create environment variables in Render:


---

## 🗄️ Database Tables

Run this SQL in Render PostgreSQL:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT
);

CREATE TABLE resumes (
    id SERIAL PRIMARY KEY,
    filename TEXT,
    match_score INT,
    skills TEXT,
    user_id INT
);

pip install -r requirements.txt
python app.py

👨‍💻 Author
Keshav Patil
