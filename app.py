from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import mysql.connector
import qrcode
import io
import base64
import secrets
from datetime import datetime, timedelta
import pandas as pd

# ================= CONFIG =================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "attendance_db"
}

QR_DEFAULT_SECONDS = 20

app = Flask(__name__)
app.secret_key = "super_secret_key"


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def create_qr(url):
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ================= AUTH =================
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM professors WHERE username=%s AND password=%s",
                    (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["prof_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")
        else:
            flash("Invalid Credentials", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "prof_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM sections WHERE professor_id=%s",
                (session["prof_id"],))
    sections = cur.fetchall()

    cur.execute("""
        SELECT q.*, s.section_name 
        FROM qr_sessions q
        JOIN sections s ON q.section_id = s.id
        WHERE s.professor_id=%s
        ORDER BY q.created_at DESC
    """, (session["prof_id"],))
    sessions_data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("dashboard.html",
                           sections=sections,
                           sessions=sessions_data)


# ================= ADD SECTION =================
@app.route("/add_section", methods=["POST"])
def add_section():
    name = request.form["section_name"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO sections (section_name, professor_id) VALUES (%s,%s)",
                (name, session["prof_id"]))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/dashboard")


# ================= ADD STUDENT =================
@app.route("/add_student", methods=["POST"])
def add_student():
    if "prof_id" not in session:
        return redirect("/login")

    section_id = request.form["section_id"]
    name = request.form["name"]
    reg = request.form["reg_no"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO students (name, reg_no, section_id)
        VALUES (%s, %s, %s)
    """, (name, reg, section_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/dashboard")



# ================= GENERATE QR =================
@app.route("/generate_qr", methods=["POST"])
def generate_qr():
    class_name = request.form["class_name"]
    ttl = int(request.form["ttl"])
    section_id = request.form["section_id"]

    token = secrets.token_urlsafe(6)
    expires = datetime.utcnow() + timedelta(seconds=ttl)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO qr_sessions (token, class_name, section_id, expires_at)
        VALUES (%s,%s,%s,%s)
    """, (token, class_name, section_id, expires))
    conn.commit()
    cur.close()
    conn.close()

    qr_url = request.host_url + "student?token=" + token
    qr_img = create_qr(qr_url)

    return render_template("generate_qr.html",
                           qr_data=qr_img,
                           ttl=ttl,
                           class_name=class_name)


# ================= STUDENT =================
@app.route("/student", methods=["GET", "POST"])
def student():
    token = request.args.get("token")

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM qr_sessions WHERE token=%s", (token,))
    qr = cur.fetchone()

    if not qr or datetime.utcnow() > qr["expires_at"]:
        return "QR Expired"

    if request.method == "POST":
        reg = request.form["reg_no"]

        cur.execute("SELECT * FROM students WHERE reg_no=%s AND section_id=%s",
                    (reg, qr["section_id"]))
        student = cur.fetchone()

        if not student:
            return "Student not found in this section"

        try:
            cur.execute("INSERT INTO attendance (session_id, student_id) VALUES (%s,%s)",
                        (qr["id"], student["id"]))
            conn.commit()
        except:
            return "Already Marked"

        return "Attendance Marked"

    return render_template("student.html")


# ================= EXPORT =================
@app.route("/export/<int:session_id>")
def export(session_id):
    conn = get_db()

    students = pd.read_sql("""
        SELECT st.id, st.name, st.reg_no
        FROM students st
        JOIN qr_sessions q ON st.section_id = q.section_id
        WHERE q.id=%s
    """, conn, params=(session_id,))

    present = pd.read_sql("""
        SELECT student_id FROM attendance
        WHERE session_id=%s
    """, conn, params=(session_id,))

    students["Status"] = students["id"].isin(present["student_id"])
    students["Status"] = students["Status"].map({True: "Present", False: "Absent"})

    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        students.to_excel(writer, index=False)

    out.seek(0)
    return send_file(out,
                     download_name="attendance.xlsx",
                     as_attachment=True)
@app.route("/analytics/<int:section_id>")
def analytics(section_id):
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    df = pd.read_sql("""
        SELECT 
            DATE(a.timestamp) as date,
            COUNT(a.id) as present_count
        FROM attendance a
        JOIN qr_sessions q ON a.session_id = q.id
        WHERE q.section_id = %s
        GROUP BY DATE(a.timestamp)
        ORDER BY DATE(a.timestamp)
    """, conn, params=(section_id,))

    conn.close()

    dates = df["date"].astype(str).tolist()
    counts = df["present_count"].tolist()

    return render_template(
        "analytics.html",
        dates=dates,
        counts=counts
    )
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    message = None
    error = None

    if request.method == "POST":
        username = request.form.get("username")

        if not username:
            error = "Please enter a username"
        else:
            conn= get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT password FROM professors WHERE username=%s",
                (username,)
            )
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user:
                message = f"Password is: {user['password']} (demo only)"
            else:
                error = "Username not found"

    return render_template("forgot.html", message=message, error=error)
# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    message = None
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            error = "All fields are required"
        else:
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO professors (username, password) VALUES (%s,%s)",
                    (username, password)
                )
                conn.commit()
                cur.close()
                conn.close()
                message = "Registration successful. You can login now."
            except:
                error = "Username already exists"

    return render_template("register.html", message=message, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
