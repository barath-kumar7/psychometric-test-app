
# Psychometric Test Web App (Excel Engineering College)

## What this does
- Student-facing web form for 50-question psychometric test.
- Generates **Student PDF** (shows only overall percentage, level, and recommendations — no raw scores).
- Generates **Teacher PDF** saved on the server with full scores and per-question answers.
- Password-protected teacher dashboard to download reports and export CSV.
- Default teacher username/password for testing: `teacher` / `password` (change on host via env vars).

## Quick local run
1. Create and activate a virtualenv (recommended):
   python3 -m venv venv
   source venv/bin/activate

2. Install dependencies:
   pip install -r requirements.txt

3. Run:
   python app.py

4. Open in browser:
   Student: http://127.0.0.1:5000
   Teacher login: http://127.0.0.1:5000/teacher/login  (use teacher/password)

## Deploy
- Push to GitHub and deploy to Railway/Render. Set environment variables on host as needed:
  - FLASK_SECRET (recommended)
  - TEACHER_USER, TEACHER_PASS (optional; if not set the defaults above will be used)
