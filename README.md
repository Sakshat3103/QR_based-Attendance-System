# 🎓 AttendX – Smart Attendance Management System

## 📌 What is this project?

AttendX is a simple web-based attendance system that helps teachers take attendance using QR codes — while preventing proxy (fake) attendance.

You do NOT need any special app. It works directly in your browser.

---

## 🚀 What can it do?

* ✅ Generate QR code for attendance
* ✅ Students scan and mark attendance
* ✅ Prevent proxy using multiple checks
* ✅ Auto-generate attendance reports
* ✅ Works on phone and laptop

---

## 🧰 Requirements (What you need before running)

Make sure you have:

1. **Python installed (version 3.10 or above)**
   👉 Download: https://www.python.org/downloads/

2. **Internet browser**
   (Chrome recommended)

---
## Project Links

https://atttendx.pythonanywhere.com/%0A

## ⚙️ How to Run the Project (Step-by-Step)

### Step 1: Download the Project

* Click the green **Code** button on GitHub
* Click **Download ZIP**
* Extract the ZIP file

---

### Step 2: Open the Project Folder

* Open the extracted folder
* You should see files like:

  * `backend/`
  * `frontend/`
  * `main.py`

---

### Step 3: Open Terminal / Command Prompt

Inside the project folder:

👉 On Windows:

* Right click → Open in Terminal

👉 Or manually:

```bash
cd path_to_project_folder
```

---

### Step 4: Install Required Libraries

Run this command:

```bash
pip install -r requirements.txt
```

---

### Step 5: Start the Project

Run:

```bash
python run.py
```

---

### Step 6: Open in Browser

After running, open:

👉 http://127.0.0.1:8000

---

## 👨‍🏫 How to Use

### For Teacher:

1. Register / Login
2. Create a section
3. Add students
4. Generate QR session
5. Show QR in class

---

### For Students:

1. Scan QR code using phone
2. Enter registration number
3. Attendance is marked instantly

---

## 🔐 How it Prevents Proxy Attendance

AttendX uses 5 security layers:

1. QR Code expires quickly
2. Only valid students allowed
3. No duplicate attendance allowed
4. One device = one attendance
5. GPS location check

---

## 📂 Project Structure

```
backend/      → Server and API logic
frontend/     → Website UI
main.py       → Main backend file
run.py        → Start the project
```

---

## 🌐 Deployment

This project can also be hosted online (example: PythonAnywhere)

---

## 👨‍💻 Developed By

* Sakshat Jain

---

## 🙌 Acknowledgement

Thanks to faculty and mentors for guidance in this project.
