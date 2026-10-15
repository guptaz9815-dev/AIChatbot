import os
from datetime import datetime
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-development-secret")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "ai_chatbot"),
}

def db():
    return mysql.connector.connect(**DB_CONFIG)

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Administrator access required.", "error")
            return redirect(url_for("chat"))
        return fn(*args, **kwargs)
    return wrapped

def knowledge_answer(question):
    """Simple keyword-based fallback. Replace/extend with embeddings or an AI API."""
    conn = db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT question, answer FROM knowledge_base WHERE is_active=1")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    q = question.lower()
    for row in rows:
        words = [w for w in row["question"].lower().split() if len(w) > 3]
        if any(w in q for w in words):
            return row["answer"]
    return "I’m not certain about that yet. Please share a little more detail, or contact our support team."

def generate_answer(question):
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI and api_key:
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a helpful customer-support chatbot. Be concise, polite, and do not invent account-specific facts."},
                    {"role": "user", "content": question},
                ],
                max_tokens=350,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            app.logger.exception("AI provider request failed; using knowledge base fallback.")
    return knowledge_answer(question)

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("admin_dashboard" if session.get("role") == "admin" else "chat"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, password_hash, role FROM users WHERE email=%s AND is_active=1", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], email=user["email"], role=user["role"])
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "chat"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email, and a password of at least 8 characters.", "error")
            return render_template("register.html")
        conn = db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users(name,email,password_hash,role) VALUES(%s,%s,%s,'user')",
                        (name, email, generate_password_hash(password)))
            conn.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            flash("That email is already registered.", "error")
        finally:
            cur.close()
            conn.close()
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html")

@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify(error="Please enter a message."), 400
    if len(message) > 4000:
        return jsonify(error="Message is too long (maximum 4000 characters)."), 400
    answer = generate_answer(message)
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations(user_id,user_message,bot_response) VALUES(%s,%s,%s)",
                (session["user_id"], message, answer))
    conn.commit()
    conversation_id = cur.lastrowid
    cur.close()
    conn.close()
    return jsonify(answer=answer, conversation_id=conversation_id, timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"))

@app.route("/history")
@login_required
def history():
    conn = db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT id,user_message,bot_response,created_at FROM conversations
                   WHERE user_id=%s ORDER BY created_at DESC LIMIT 100""", (session["user_id"],))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("history.html", rows=rows)

@app.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    if request.method == "POST":
        rating = request.form.get("rating", "5")
        comments = request.form.get("comments", "").strip()
        category = request.form.get("category", "General")
        try:
            rating = max(1, min(5, int(rating)))
        except ValueError:
            rating = 5
        conn = db()
        cur = conn.cursor()
        cur.execute("INSERT INTO feedback(user_id,rating,category,comments) VALUES(%s,%s,%s,%s)",
                    (session["user_id"], rating, category, comments))
        conn.commit()
        cur.close()
        conn.close()
        flash("Thank you! Your feedback has been submitted.", "success")
        return redirect(url_for("feedback"))
    return render_template("feedback.html")

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS total FROM conversations")
    total = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(DISTINCT user_id) AS total FROM conversations")
    users = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM feedback")
    feedback_count = cur.fetchone()["total"]
    cur.execute("SELECT ROUND(AVG(rating),1) AS avg_rating FROM feedback")
    avg_rating = cur.fetchone()["avg_rating"] or 0
    cur.execute("SELECT id,user_message,bot_response,created_at FROM conversations ORDER BY created_at DESC LIMIT 8")
    recent = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin.html", total=total, users=users, feedback_count=feedback_count,
                           avg_rating=avg_rating, recent=recent)

@app.route("/admin/knowledge", methods=["GET", "POST"])
@admin_required
def knowledge():
    conn = db()
    cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()
        if question and answer:
            cur.execute("INSERT INTO knowledge_base(question,answer) VALUES(%s,%s)", (question, answer))
            conn.commit()
            flash("Knowledge-base entry added.", "success")
        else:
            flash("Both question and answer are required.", "error")
    cur.execute("SELECT id,question,answer,is_active FROM knowledge_base ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("knowledge.html", rows=rows)

@app.route("/admin/knowledge/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_knowledge(item_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM knowledge_base WHERE id=%s", (item_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Knowledge-base entry deleted.", "success")
    return redirect(url_for("knowledge"))

@app.route("/admin/feedback")
@admin_required
def admin_feedback():
    conn = db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT f.rating,f.category,f.comments,f.created_at,u.name,u.email
                   FROM feedback f JOIN users u ON u.id=f.user_id ORDER BY f.created_at DESC LIMIT 100""")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_feedback.html", rows=rows)

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
