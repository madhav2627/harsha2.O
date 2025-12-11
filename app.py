# ------------------------------
# Harsha AI — Full System Backend (Part 1/3)
# ------------------------------

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, send_file
)
from flask_session import Session
import sqlite3
import os
import datetime
import pytz
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps


# ------------------------------
# 1. App Setup
# ------------------------------

app = Flask(__name__)
app.secret_key = "harsha_secret_key"
app.config["SESSION_TYPE"] = "filesystem"
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
Session(app)


# ------------------------------
# 2. Database Setup
# ------------------------------

DB_PATH = "data/users.db"
os.makedirs("data", exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            created_at TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            info TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            rating INTEGER,
            timestamp TEXT
        );
    """)

    conn.commit()
    conn.close()

init_db()


# ------------------------------
# 3. Login Required Wrapper
# ------------------------------

def login_required(f):
    @wraps(f)
    def protected(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return protected


# ------------------------------
# 4. Time Helper (IST)
# ------------------------------

def get_indian_time():
    utc = pytz.utc.localize(datetime.datetime.utcnow())
    ist = utc.astimezone(pytz.timezone("Asia/Kolkata"))
    return ist.strftime("%I:%M %p")


# ------------------------------
# 5. Database Message Helpers
# ------------------------------

def save_message(user_id, role, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, role, content, datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def load_messages(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE user_id=? ORDER BY id ASC",
        (user_id,)
    ).fetchall()
    conn.close()

    return [{"who": r["role"], "text": r["content"]} for r in rows]


# ------------------------------
# 6. Memory Helpers
# ------------------------------

def save_memory(user_id, topic, info):
    conn = get_db()
    conn.execute(
        "INSERT INTO memory (user_id, topic, info) VALUES (?, ?, ?)",
        (user_id, topic, info)
    )
    conn.commit()
    conn.close()

def get_memory(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT topic, info FROM memory WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return rows

def search_memory(user_id, keyword):
    conn = get_db()
    rows = conn.execute(
        "SELECT info FROM memory WHERE user_id=? AND topic LIKE ?",
        (user_id, f"%{keyword}%")
    ).fetchall()
    conn.close()
    return rows


# ------------------------------
# 7. File Upload Helper
# ------------------------------

def save_uploaded_file(file):
    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    return path


# ------------------------------
# END OF PART 1
# ------------------------------

# ------------------------------
# Harsha AI — AI Engine (Part 2/3)
# ------------------------------

# --------------------------------
# EXTERNAL API HELPERS
# --------------------------------

def get_wikipedia_summary(query):
    try:
        import wikipedia
        return wikipedia.summary(query, sentences=2)
    except:
        return None

def get_dictionary_meaning(word):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        data = requests.get(url).json()
        return data[0]['meanings'][0]['definitions'][0]['definition']
    except:
        return None

def get_joke():
    try:
        url = "https://official-joke-api.appspot.com/random_joke"
        j = requests.get(url).json()
        return f"{j['setup']} — {j['punchline']}"
    except:
        return "Couldn't fetch a joke right now 🙂"

def get_advice():
    try:
        url = "https://api.adviceslip.com/advice"
        a = requests.get(url).json()
        return a["slip"]["advice"]
    except:
        return "Couldn't fetch advice right now 🙂"

def get_weather(city):
    try:
        api_key = "no_api_key"  # add your key if needed
        url = f"https://wttr.in/{city}?format=3"
        return requests.get(url).text
    except:
        return None


# --------------------------------
# PERSONALITY FORMATTER
# --------------------------------

def buddy_style(text):
    """
    Friendly Buddy personality:
    - Light emojis only
    - Casual friendly tone
    - Encouraging
    """
    return f"{text} 🙂"


# --------------------------------
# MAIN AI RESPONSE LOGIC
# --------------------------------

def ai_response(user_id, text):
    original = text
    text = text.lower().strip()

    # --------------------------
    # 1. Greetings
    # --------------------------
    if text in ["hi", "hello", "hey", "yo"]:
        return buddy_style(f"Hey {session.get('username')}! What's up?")

    # --------------------------
    # 2. Time / Date
    # --------------------------
    if "time" in text:
        return buddy_style(f"The current time (IST) is {get_indian_time()}.")

    if "date" in text:
        today = datetime.datetime.now().strftime("%d %B %Y")
        return buddy_style(f"Today's date is {today}.")

    # --------------------------
    # 3. Memory: What do you remember?
    # --------------------------
    if "what do you remember" in text:
        mem = get_memory(user_id)
        if not mem:
            return buddy_style("I don't have any memories saved yet.")
        lines = [f"- {m['topic']}: {m['info']}" for m in mem]
        return buddy_style("Here's what I remember:\n" + "\n".join(lines))

    # --------------------------
    # 4. Teach the AI: "Remember that ..."
    # --------------------------
    if text.startswith("remember that"):
        info = original.replace("remember that", "").strip()
        if len(info) < 3:
            return buddy_style("Can you tell me something meaningful to remember?")
        
        topic = info.split(" ")[0]
        save_memory(user_id, topic, info)
        return buddy_style("Got it! I'll remember that 🙂")

    # --------------------------
    # 5. Search Memory (per user)
    # --------------------------
    words = text.split()
    for w in words:
        mem_hits = search_memory(user_id, w)
        if mem_hits:
            return buddy_style(mem_hits[0]["info"])

    # --------------------------
    # 6. Meaning of a word
    # --------------------------
    if text.startswith("meaning of"):
        word = text.replace("meaning of", "").strip()
        meaning = get_dictionary_meaning(word)
        if meaning:
            return buddy_style(f"The meaning of {word} is: {meaning}")
        else:
            return buddy_style("Couldn't find the meaning, buddy.")

    # --------------------------
    # 7. Weather
    # --------------------------
    if text.startswith("weather in"):
        city = text.replace("weather in", "").strip()
        w = get_weather(city)
        if w:
            return buddy_style(f"Here's the weather update: {w}")
        return buddy_style("Couldn't fetch weather.")

    # --------------------------
    # 8. Jokes
    # --------------------------
    if "joke" in text:
        return buddy_style(get_joke())

    # --------------------------
    # 9. Advice
    # --------------------------
    if "advice" in text:
        return buddy_style(get_advice())

    # --------------------------
    # 10. Wikipedia fallback
    # --------------------------
    wiki = get_wikipedia_summary(text)
    if wiki:
        return buddy_style(wiki)

    # --------------------------
    # 11. Default fallback
    # --------------------------
    return buddy_style("Hmm, I’m not fully sure about that, but I'm learning everyday! Try asking differently 🙂")


# ------------------------------
# END OF PART 2
# ------------------------------

# ------------------------------
# Harsha AI — Routes (Part 3/3)
# ------------------------------

# ------------------------------
# SIGNUP
# ------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if len(username) < 3:
            flash("Username must be at least 3 chars.")
            return redirect(url_for("signup"))

        if len(password) < 4:
            flash("Password must be at least 4 chars.")
            return redirect(url_for("signup"))

        db = get_db()

        try:
            db.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), datetime.datetime.now().isoformat())
            )
            db.commit()
            flash("Account created! Login now.")
            return redirect(url_for("login"))
        except:
            flash("Username already exists.")

        db.close()

    return render_template("signup.html")


# ------------------------------
# LOGIN
# ------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = username
            return redirect(url_for("index"))

        flash("Invalid username or password.")

    return render_template("login.html")


# ------------------------------
# LOGOUT
# ------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------
# HOME (CHAT PAGE)
# ------------------------------
@app.route("/")
@login_required
def index():
    messages = load_messages(session["user_id"])
    return render_template(
        "index.html",
        user=session["username"],
        messages=messages
    )


# ------------------------------
# SEND MESSAGE (Normal Chat)
# ------------------------------
@app.route("/send", methods=["POST"])
@login_required
def send():
    user_id = session["user_id"]
    text = request.form.get("message")

    # Save user message
    save_message(user_id, "user", text)

    # Generate AI reply
    reply = ai_response(user_id, text)

    # Save bot message
    save_message(user_id, "bot", reply)

    return redirect(url_for("index"))


# ------------------------------
# API CHAT (AJAX / JS Support)
# ------------------------------
@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.get_json()
    user_msg = data.get("message", "")
    user_id = session["user_id"]

    save_message(user_id, "user", user_msg)
    bot_reply = ai_response(user_id, user_msg)
    save_message(user_id, "bot", bot_reply)

    return jsonify({"reply": bot_reply})


# ------------------------------
# RESET CHAT (Clear all messages)
# ------------------------------
@app.route("/reset")
@login_required
def reset_chat():
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    flash("Chat cleared.")
    return redirect(url_for("index"))


# ------------------------------
# PROFILE PAGE
# ------------------------------
@app.route("/profile")
@login_required
def profile():
    db = get_db()
    user = db.execute(
        "SELECT id, username, created_at FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    mem_count = db.execute(
        "SELECT COUNT(*) as c FROM memory WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()["c"]

    msg_count = db.execute(
        "SELECT COUNT(*) as c FROM messages WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()["c"]

    return render_template(
        "profile.html",
        user=user,
        memories=mem_count,
        messages=msg_count
    )


# ------------------------------
# ADMIN PAGE
# ------------------------------
@app.route("/admin")
@login_required
def admin():
    # Only allow admin user
    if session.get("username") != "admin":
        return "Access denied."

    db = get_db()
    users = db.execute("SELECT id, username, created_at FROM users").fetchall()
    return render_template("admin.html", users=users)


# ------------------------------
# FEEDBACK
# ------------------------------
@app.route("/feedback", methods=["POST"])
@login_required
def feedback():
    rating = int(request.form.get("rating", 0))
    message = request.form.get("message", "")

    uid = session["user_id"]

    conn = get_db()
    conn.execute(
        "INSERT INTO feedback (user_id, message, rating, timestamp) VALUES (?, ?, ?, ?)",
        (uid, message, rating, datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    flash("Thanks for your feedback!")
    return redirect(url_for("index"))


# ------------------------------
# FILE UPLOAD PAGE
# ------------------------------
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")

        if not file:
            flash("Please upload a file.")
            return redirect(url_for("upload"))

        path = save_uploaded_file(file)
        flash(f"Uploaded: {file.filename}")
        return redirect(url_for("upload"))

    return render_template("upload.html")


# ------------------------------
# DOWNLOAD CHAT AS TEXT FILE
# ------------------------------
@app.route("/download")
@login_required
def download_chat():
    uid = session["user_id"]
    msgs = load_messages(uid)

    text = ""
    for m in msgs:
        text += f"{m['who'].upper()}: {m['text']}\n\n"

    filename = f"chat_{uid}.txt"
    filepath = os.path.join("data", filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    return send_file(filepath, as_attachment=True)


# ------------------------------
# RUN SERVER
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)
