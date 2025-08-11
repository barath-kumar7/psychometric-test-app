
import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
from datetime import datetime
from io import BytesIO
from pathlib import Path
import csv
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change_this_secret")

# Config: default teacher creds for testing (you can change or set env vars later)
TEACHER_USER = os.environ.get("TEACHER_USER", "teacher")
TEACHER_PASS = os.environ.get("TEACHER_PASS", "password")

INSTITUTION_NAME = "Excel Engineering College (Autonomous)"

DATA_DIR = Path("teacher_reports")
DATA_DIR.mkdir(exist_ok=True)
CSV_FILE = Path("submissions.csv")

# Questions (from the provided PDFs)
LIKERT_QUESTIONS = [
"I enjoy meeting new people and easily initiate conversations.",
"I pay attention to details and prefer planning before acting.",
"I remain calm even in stressful situations.",
"I am curious and open to trying new ideas and methods.",
"I work well independently without constant supervision.",
"I am usually enthusiastic and energetic.",
"I follow through with tasks I start.",
"I get upset or nervous easily.",
"I value creative approaches to problem-solving.",
"I adapt well to new environments and changes.",
"I understand how my emotions influence my decisions.",
"I can control my emotions even when I feel stressed.",
"I empathize easily with other people’s feelings.",
"I maintain calm during difficult conversations.",
"I can read non-verbal cues like tone and body language.",
"I try to resolve conflicts instead of avoiding them.",
"I accept constructive criticism without taking it personally.",
"I encourage others when they feel low or demotivated.",
"I am aware of my strengths and weaknesses.",
"I listen actively during conversations.",
"I can express my ideas clearly in both written and spoken formats.",
"I listen carefully and do not interrupt while others are talking.",
"I adjust my communication style based on the audience.",
"I feel confident while speaking in group discussions or interviews.",
"I maintain eye contact and appropriate body language when speaking.",
"I can handle questions or objections calmly.",
"I am able to structure my answers logically during interviews.",
"I ask relevant questions when I don’t understand something.",
"I respond to feedback professionally and politely.",
"I can summarize my views effectively without rambling.",
"I enjoy working with machines, tools, or animals.",
"I like solving puzzles or analysing scientific data.",
"I enjoy music, writing, art, or drama.",
"I like helping people solve their problems.",
"I enjoy leading teams or selling ideas.",
"I prefer working with numbers, data, and organized tasks.",
"I feel most satisfied when I work on hands-on tasks.",
"I would enjoy doing research or investigative writing.",
"I feel motivated when I can teach or counsel others.",
"I prefer roles where I can organize files, reports, or systems."
]

# MCQs for 41..50 with options text (we will save answers; SJT scoring key below)
MCQ_QUESTIONS = [
("You are asked a question in an interview but don’t know the answer. What do you do?", ["A. Make up an answer that sounds good.", "B. Admit you don’t know and stay silent.", "C. Politely acknowledge it and mention how you would find the answer.", "D. Try to divert the question."]),
("During a group interview, a teammate is dominating. You:", ["A. Argue and challenge him.", "B. Let them continue to avoid conflict.", "C. Wait and then calmly ask to share your view.", "D. Ignore the discussion."]),
("The interviewer gives feedback that your response lacked clarity. You:", ["A. Get defensive and justify yourself.", "B. Say “okay” but don’t respond.", "C. Ask politely for clarification and offer a better answer.", "D. Change the topic."]),
("You forgot an important document before your interview. You:", ["A. Panic and cancel the interview.", "B. Attend and apologize, explaining honestly.", "C. Blame someone else.", "D. Skip the question if asked."]),
("You’re asked about a weakness. You:", ["A. Say “I have none.”", "B. Mention a weakness and how you’re improving.", "C. Give a fake strength as a weakness.", "D. Avoid answering."]),
("You are working on a group project. One team member is not contributing and is avoiding responsibilities, which is affecting the group’s progress. What would you most likely do?", ["A. Do their part of the work silently to avoid conflict", "B. Confront them publicly in front of the team", "C. Speak to them privately and try to understand their side", "D. Complain to the teacher without discussing with the team member"]),
("You notice your friend cheating during an important online test. You know they are struggling with academics. What would you most likely do?", ["A. Ignore it – they’re your friend and need help", "B. Tell the teacher immediately", "C. Confront your friend privately and advise them not to do it again", "D. Warn them during the test to stop"]),
("During a mock interview, you're asked a technical question you don’t know the answer to. What would you most likely do?", ["A. Try to bluff and answer vaguely", "B. Admit you don’t know and remain silent", "C. Say, “I’m not sure, but I’d approach it by…” and describe your thinking process", "D. Skip the question entirely and hope it’s not noticed"]),
("You send a message to a classmate that they misinterpret and now they seem upset. What would you most likely do?", ["A. Ignore it — they’ll get over it", "B. Clarify what you meant and apologize if it caused confusion", "C. Ask others to explain it to them", "D. Block them to avoid confrontation"]),
("You are selected as the team leader for an event. Just a day before the event, your two key volunteers drop out. What would you most likely do?", ["A. Panic and cancel the event", "B. Blame them publicly and ask others to replace them", "C. Calmly reassess roles, delegate efficiently, and motivate your team", "D. Try to do everything yourself"])
]

SJT_KEY = {
  41: {'A':1,'B':2,'C':4,'D':3},
  42: {'A':1,'B':2,'C':4,'D':3},
  43: {'A':1,'B':2,'C':4,'D':3},
  44: {'A':1,'B':4,'C':2,'D':3},
  45: {'A':1,'B':4,'C':3,'D':2},
  46: {'A':2,'B':1,'C':4,'D':3},
  47: {'A':2,'B':1,'C':4,'D':3},
  48: {'A':1,'B':2,'C':4,'D':3},
  49: {'A':1,'B':4,'C':2,'D':3},
  50: {'A':1,'B':2,'C':4,'D':3}
}

# Section mapping and maxes
SECTION_MAP = {
    'Personality (OCEAN)': range(1,11),
    'Emotional Intelligence (EQ)': range(11,21),
    'Communication Skills': range(21,31),
    'Career Interest (RIASEC)': range(31,41),
    'Situational Judgment Test (SJT)': range(41,51)
}
SECTION_MAX = {
    'Personality (OCEAN)': 50,
    'Emotional Intelligence (EQ)': 50,
    'Communication Skills': 50,
    'Career Interest (RIASEC)': 50,
    'Situational Judgment Test (SJT)': 40
}

# thresholds & recommendation functions (from your detail explanation)
def overall_level_and_recommendation(pct):
    if pct >= 85:
        return "Exceptional", "You are highly prepared for both academic and professional settings. Recommendations: Take on mentoring roles, join advanced training in emotional intelligence or strategic thinking, participate in high-stakes projects."
    if pct >= 70:
        return "Proficient", "Solid foundation; most skills are well-developed. Recommendations: Real-world exposure, advanced communication and leadership workshops, regular practice with mock interviews."
    if pct >= 55:
        return "Developing", "Emerging potential; some traits need strengthening. Recommendations: Join personality development and soft skills training programs, work with a mentor, practice role-play and GDs."
    if pct >= 40:
        return "Basic Awareness", "Foundational awareness but inconsistent application. Recommendations: Foundational workshops on communication and EI, structured self-help tools, weekly improvement goals."
    return "Needs Attention", "Significant skill gaps. Recommendations: Attend beginner workshops, one-on-one mentoring, structured PDP."

def section_level_and_recommendation(section, score):
    max_s = SECTION_MAX[section]
    if section == 'Situational Judgment Test (SJT)':
        if score >= 36: return "Exceptional", "Outstanding judgment and professionalism. Keep practicing leadership scenarios."
        if score >= 31: return "Good", "Strong situational judgment; minor refinements recommended."
        if score >= 21: return "Average", "Practice mock interviews and situational role-play to build confidence."
        if score >= 11: return "Needs Improvement", "Work on basic decision-making skills through workshops."
        return "Critical Concern", "Immediate support recommended."
    # For 50-point sections use percentage bands similar to PDF
    pct = (score / max_s) * 100 if max_s else 0
    if pct >= 80: return "Excellent", "Strong skill — leverage for leadership and mentoring opportunities."
    if pct >= 60: return "Good", "Solid skill; refine with targeted practice and workshops."
    if pct >= 40: return "Developing", "Work on consistency and applied practice through role-play and training."
    if pct >= 20: return "Basic Awareness", "Start with foundational training and practice."
    return "Needs Improvement", "Immediate guided practice and mentoring recommended."

# helper to compute scores
def compute_scores(answers):
    per_q = {}
    # likert 1..40 stored as "5"/"4"... convert to int
    for i in range(1,41):
        v = answers.get(str(i))
        per_q[i] = int(v) if v and v.isdigit() else 0
    # MCQ 41..50
    for i in range(41,51):
        v = answers.get(str(i))
        per_q[i] = SJT_KEY.get(i, {}).get(v, 0)
    # section totals
    section_scores = {}
    for sec, rng in SECTION_MAP.items():
        s = sum(per_q[q] for q in rng)
        section_scores[sec] = s
    total = sum(section_scores.values())
    max_total = sum(SECTION_MAX.values())
    return section_scores, total, max_total, per_q

# PDF helpers: draw justified paragraph
def draw_paragraph_justified(c, text, x, y, max_width, leading=12, fontname="Helvetica", fontsize=10):
    words = text.split()
    lines = []
    line = []
    for w in words:
        test = " ".join(line + [w])
        if c.stringWidth(test, fontname, fontsize) <= max_width:
            line.append(w)
        else:
            lines.append(line)
            line = [w]
    if line:
        lines.append(line)
    cur_y = y
    for idx, line_words in enumerate(lines):
        if not line_words:
            cur_y -= leading
            continue
        line_text = " ".join(line_words)
        if idx != len(lines)-1:
            # justify: distribute extra space
            total_words_width = sum(c.stringWidth(w, fontname, fontsize) for w in line_words)
            spaces = len(line_words)-1 if len(line_words)>1 else 1
            extra = max_width - total_words_width
            space_width = extra / spaces
            cur_x = x
            for j, w in enumerate(line_words):
                c.drawString(cur_x, cur_y, w)
                cur_x += c.stringWidth(w, fontname, fontsize) + space_width
        else:
            # last line: left align
            c.drawString(x, cur_y, line_text)
        cur_y -= leading
    return cur_y

def generate_student_pdf(student_info, section_scores, total, max_total, section_levels):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20*mm
    y = height - margin
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y, INSTITUTION_NAME)
    y -= 18
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, y, "Psychometric Test Report - Navigating the Interview")
    y -= 20

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, f"Name: {student_info.get('name')}")
    c.drawRightString(width - margin, y, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Roll No.: {student_info.get('rollno')}")
    c.drawString(margin+220, y, f"Department: {student_info.get('department')}")
    y -= 18

    pct = round((total/max_total)*100,2) if max_total else 0
    overall_level, overall_rec = overall_level_and_recommendation(pct)

    # color bar for overall level
    bar_x = margin
    bar_y = y - 8
    bar_w = width - 2*margin
    bar_h = 8
    # color mapping
    if pct >= 85:
        color = (0.0, 0.5, 0.0) # dark green
    elif pct >= 70:
        color = (0.0, 0.6, 0.8) # teal
    elif pct >= 55:
        color = (0.8, 0.6, 0.0) # amber
    elif pct >= 40:
        color = (0.9, 0.4, 0.0) # orange
    else:
        color = (0.8, 0.0, 0.0) # red
    c.setFillColorRGB(*color)
    c.rect(bar_x, bar_y, bar_w * (pct/100.0), bar_h, fill=1, stroke=0)
    c.setFillColorRGB(0,0,0)
    y = bar_y - 16

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Overall Result")
    y -= 12
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Overall Percentage: {pct}%")
    c.drawRightString(width - margin, y, f"Level: {overall_level}")
    y -= 14

    # overall recommendation (justified)
    c.setFont("Helvetica", 10)
    y = draw_paragraph_justified(c, overall_rec, margin, y, width - 2*margin, leading=12, fontsize=10)
    y -= 8

    # Section summaries: show level and recommendation (JUSTIFIED)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Section-wise Levels & Recommendations")
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    for sec, (lvl, rec) in section_levels.items():
        c.drawString(margin, y, f"{sec}: {lvl}")
        y -= 12
        c.setFont("Helvetica", 10)
        y = draw_paragraph_justified(c, rec, margin+8, y, width - 2*margin - 8, leading=11, fontsize=10)
        y -= 10
        c.setFont("Helvetica-Bold", 10)
        if y < 80:
            c.showPage()
            y = height - margin

    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width/2, 18, "This student-facing report contains levels & recommendations only. Raw scores are confidential.")
    c.save()
    buffer.seek(0)
    return buffer

def generate_teacher_pdf(student_info, section_scores, total, max_total, per_q_scores, answers):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in student_info.get("name","Unknown") if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
    filename = DATA_DIR / f"TeacherReport_{safe_name}_{timestamp}.pdf"
    c = canvas.Canvas(str(filename), pagesize=A4)
    width, height = A4
    margin = 16*mm
    y = height - margin
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Teacher Detailed Report")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Student: {student_info.get('name')}   Roll: {student_info.get('rollno')}   Dept: {student_info.get('department')}")
    c.drawRightString(width - margin, y, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 14

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Section Scores (raw)")
    y -= 12
    c.setFont("Helvetica", 10)
    for sec, sc in section_scores.items():
        c.drawString(margin, y, f"{sec}: {sc} / {SECTION_MAX[sec]}")
        y -= 12
        if y < 80:
            c.showPage(); y = height - margin

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, f"Total Score: {total} / {sum(SECTION_MAX.values())}   ({round((total/sum(SECTION_MAX.values()))*100,2)}%)")
    y -= 16

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Per-question responses (Q#, Answer, Score)")
    y -= 12
    c.setFont("Helvetica", 9)
    for qnum in range(1,51):
        if qnum <= 40:
            qtext = LIKERT_QUESTIONS[qnum-1]
            ans = answers.get(str(qnum))
            sc = per_q_scores.get(qnum, 0)
            line = f"{qnum}. {qtext} — Answer: {ans} — Score: {sc}"
        else:
            qtext = MCQ_QUESTIONS[qnum-41][0]
            ans = answers.get(str(qnum))
            sc = per_q_scores.get(qnum, 0)
            line = f"{qnum}. {qtext} — Answer: {ans} — Score: {sc}"
        if len(line) > 120:
            c.drawString(margin, y, line[:120])
            y -= 10
            c.drawString(margin+8, y, line[120:])
            y -= 12
        else:
            c.drawString(margin, y, line)
            y -= 12
        if y < 80:
            c.showPage(); y = height - margin
    c.save()
    return filename

# CSV initialization
if not CSV_FILE.exists():
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["timestamp","name","rollno","department","classSection","email","total","percentage"]
        header += list(SECTION_MAP.keys())
        writer.writerow(header)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", likert_questions=LIKERT_QUESTIONS, mcq_questions=[q for q,_ in MCQ_QUESTIONS])

@app.route("/submit", methods=["POST"])
def submit():
    student_info = {
        "name": request.form.get("studentName","").strip(),
        "rollno": request.form.get("rollNumber","").strip(),
        "department": request.form.get("department","").strip(),
        "classSection": request.form.get("classSection","").strip(),
        "email": request.form.get("studentEmail","").strip()
    }
    # gather answers
    answers = {}
    for i in range(1,51):
        val = request.form.get(f"q{i}")
        if val is None:
            return "Please answer all questions before submitting.", 400
        answers[str(i)] = val
    # compute
    section_scores, total, max_total, per_q_scores = compute_scores(answers)
    # section levels
    section_levels = {}
    for sec, sc in section_scores.items():
        lvl, rec = section_level_and_recommendation(sec, sc)
        section_levels[sec] = (lvl, rec)
    # generate student pdf
    student_pdf = generate_student_pdf(student_info, section_scores, total, max_total, section_levels)
    # save teacher pdf to server
    teacher_pdf_path = generate_teacher_pdf(student_info, section_scores, total, max_total, per_q_scores, answers)
    # append CSV
    row = [datetime.now().isoformat(), student_info["name"], student_info["rollno"], student_info["department"], student_info["classSection"], student_info["email"], total, round((total/max_total)*100,2)]
    for sec in SECTION_MAP.keys():
        row.append(section_scores.get(sec,0))
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)
    # return student pdf for immediate download
    student_pdf.seek(0)
    fname = f"Student_Report_{student_info['name'].replace(' ','_')}.pdf"
    return send_file(student_pdf, as_attachment=True, download_name=fname, mimetype="application/pdf")

# Teacher panel
@app.route("/teacher/login", methods=["GET","POST"])
def teacher_login():
    if request.method == "POST":
        user = request.form.get("user")
        pwd = request.form.get("pwd")
        if user == TEACHER_USER and pwd == TEACHER_PASS:
            session["teacher"] = True
            return redirect(url_for("teacher_dashboard"))
        flash("Invalid credentials")
    return render_template("teacher_login.html")

def teacher_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("teacher"):
            return redirect(url_for("teacher_login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/teacher/logout")
def teacher_logout():
    session.pop("teacher", None)
    return redirect(url_for("teacher_login"))

@app.route("/teacher/dashboard")
@teacher_required
def teacher_dashboard():
    reports = sorted(DATA_DIR.glob("TeacherReport_*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    recent = []
    if CSV_FILE.exists():
        with open(CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                recent.append(row)
    return render_template("teacher_dashboard.html", reports=reports, recent=recent[:50])

@app.route("/teacher/download/<path:filename>")
@teacher_required
def teacher_download(filename):
    p = DATA_DIR / filename
    if not p.exists():
        flash("File not found")
        return redirect(url_for("teacher_dashboard"))
    return send_file(str(p), as_attachment=True, download_name=filename, mimetype="application/pdf")

@app.route("/teacher/download_csv")
@teacher_required
def teacher_download_csv():
    if not CSV_FILE.exists():
        flash("No CSV available")
        return redirect(url_for("teacher_dashboard"))
    return send_file(str(CSV_FILE), as_attachment=True, download_name="submissions.csv", mimetype="text/csv")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
