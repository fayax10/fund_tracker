from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
import os

DB = os.path.join(os.getenv("RENDER_DATA_PATH", "."), "database.db")

TARGET_AMOUNT = 54400


def db():
    return sqlite3.connect(DB)

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        coupon_id TEXT PRIMARY KEY,
        student_name TEXT,
        class_name TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coupon_id TEXT,
        amount INTEGER,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data received"}), 400

    coupon_id = data.get("coupon_id")
    student_name = data.get("student_name")
    class_name = data.get("class_name")
    amount = int(data.get("amount", 0))

    if not all([coupon_id, student_name, class_name]):
        return jsonify({"error": "Missing fields"}), 400

    if amount == 0 or abs(amount) > 500:
        return jsonify({"error": "Invalid amount"}), 400

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO students (coupon_id, student_name, class_name)
        VALUES (?, ?, ?)
    """, (coupon_id, student_name, class_name))

    cur.execute("""
        INSERT INTO collections (coupon_id, amount, timestamp)
        VALUES (?, ?, ?)
    """, (coupon_id, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return jsonify({"status": "success"})
@app.route("/update")
def update():
    return render_template("update.html")


@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html")


@app.route("/leaderboard-data")
def leaderboard_data():
    conn = db()
    c = conn.cursor()

    c.execute("""
        SELECT s.student_name, s.class_name, SUM(c.amount) total
        FROM collections c
        JOIN students s ON s.coupon_id = c.coupon_id
        GROUP BY c.coupon_id
        ORDER BY total DESC
    """)

    data = c.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/stats")
def stats():
    conn = db()
    c = conn.cursor()

    # Total collection
    c.execute("SELECT SUM(amount) FROM collections")
    total = c.fetchone()[0] or 0

    # Top contributor
    c.execute("""
        SELECT s.student_name, SUM(c.amount) total
        FROM collections c
        JOIN students s ON s.coupon_id = c.coupon_id
        GROUP BY c.coupon_id
        ORDER BY total DESC
        LIMIT 1
    """)
    topper = c.fetchone()

    # Class-wise totals
    c.execute("""
        SELECT s.class_name, SUM(c.amount)
        FROM collections c
        JOIN students s ON s.coupon_id = c.coupon_id
        GROUP BY s.class_name
    """)
    classes = c.fetchall()

    conn.close()

    percentage = int((total / TARGET_AMOUNT) * 100) if TARGET_AMOUNT else 0
    percentage = min(percentage, 100)

    return jsonify({
        "total": total,
        "target": TARGET_AMOUNT,
        "percentage": percentage,
        "topper": topper,
        "classes": classes
    })

# ✅ CLASS REPORT — MUST BE HERE
@app.route("/class_report")
def class_report():
    conn = db()
    c = conn.cursor()

    c.execute("""
        SELECT s.class_name, s.student_name, SUM(c.amount) total
        FROM collections c
        JOIN students s ON s.coupon_id = c.coupon_id
        GROUP BY s.class_name, s.student_name
        ORDER BY s.class_name, total DESC
    """)

    rows = c.fetchall()
    conn.close()

    report = {}
    for cls, student, total in rows:
        report.setdefault(cls, []).append((student, total))

    return render_template("class_report.html", report=report)


@app.route("/admin/db")
def admin_db():
    conn = db()
    c = conn.cursor()
    c.execute("""
        SELECT s.student_name, s.class_name, c.amount, c.timestamp
        FROM collections c
        JOIN students s ON s.coupon_id = c.coupon_id
        ORDER BY c.timestamp DESC
    """)
    rows = c.fetchall()
    conn.close()
    return render_template("admin.html", rows=rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)