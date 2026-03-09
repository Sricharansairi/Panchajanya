"""
CurricuForge — Reminder Scheduler Module
Importable module (like pdf_generator.py) — integrated directly into app.py.

Usage in app.py:
    from reminder_scheduler import start_scheduler, save_schedule, send_test_email, get_upcoming_reminders

Call start_scheduler() once at app startup.
Call save_schedule(data) when user saves their reminder settings.
"""

import json
import os
import time
import smtplib
import schedule
import threading
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Config ────────────────────────────────────────────────────────────────────
SCHEDULE_FILE          = "reminder_schedule.json"
SENT_LOG_FILE          = "reminder_sent_log.json"
SMTP_SERVER            = "smtp.gmail.com"
SMTP_PORT              = 587
CHECK_INTERVAL_MINUTES = 60

_scheduler_started = False   # guard — only ever start one background thread


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — called from app.py
# ══════════════════════════════════════════════════════════════════════════════

def start_scheduler():
    """
    Start the background reminder thread.
    Safe to call multiple times — only one thread will ever run.
    Call this once near the top of app.py main().
    """
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True

    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(_check_and_send)

    thread = threading.Thread(target=_run_loop, daemon=True)
    thread.start()
    print("[ReminderScheduler] Background thread started.")


def save_schedule(payload: dict):
    """
    Save reminder schedule to JSON file.
    Called from app.py when user clicks Save Schedule.
    """
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(payload, f, indent=2)


def send_test_email(to_email: str, sender_email: str, sender_password: str,
                    curriculum_title: str, level: str):
    """
    Send a test email to verify credentials.
    Returns (success: bool, message: str).
    """
    subject = f"✅ CurricuForge Reminder Test — {curriculum_title}"
    body = (
        f"This is a test reminder from CurricuForge.\n\n"
        f"Curriculum : {curriculum_title}\n"
        f"Level      : {level}\n\n"
        f"Your automated semester reminders are configured correctly!\n"
        f"You will receive reminders 3 days before, 1 day before, "
        f"and on the start day of each semester.\n\n"
        f"— CurricuForge Reminder System\n"
        f"Sent: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    )
    try:
        _send_email(to_email, sender_email, sender_password, subject, body)
        return True, f"Test email sent to {to_email}!"
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed. Check your Gmail App Password."
    except Exception as e:
        return False, str(e)


def get_upcoming_reminders():
    """
    Return list of upcoming (unsent) reminders for display in the UI.
    Each item: { sem_number, sem_title, trigger, send_date }
    """
    schedule_data = _load_json(SCHEDULE_FILE, None)
    sent_log      = _load_json(SENT_LOG_FILE, {})
    if not schedule_data:
        return []

    today    = date.today()
    upcoming = []

    for sem in schedule_data.get("semesters", []):
        sem_num        = str(sem.get("semester_number", ""))
        start_date_str = sem.get("start_date", "")
        if not start_date_str:
            continue
        try:
            start = date.fromisoformat(start_date_str)
        except ValueError:
            continue

        for key, days, label in [
            ("3_days", 3, "3 days before"),
            ("1_day",  1, "1 day before"),
            ("on_day", 0, "Start day"),
        ]:
            log_key   = f"sem_{sem_num}_{key}"
            send_date = start - timedelta(days=days)
            if send_date >= today and not sent_log.get(log_key):
                upcoming.append({
                    "sem_number": sem_num,
                    "sem_title":  sem.get("semester_title", ""),
                    "trigger":    label,
                    "send_date":  send_date.strftime("%b %d, %Y"),
                })

    return sorted(upcoming, key=lambda x: x["send_date"])


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL — background loop & checker
# ══════════════════════════════════════════════════════════════════════════════

def _run_loop():
    _check_and_send()   # run once immediately on start
    while True:
        schedule.run_pending()
        time.sleep(60)


def _check_and_send():
    schedule_data = _load_json(SCHEDULE_FILE, None)
    if not schedule_data:
        return

    to_email        = schedule_data.get("to_email", "")
    sender_email    = schedule_data.get("sender_email", "")
    sender_password = schedule_data.get("sender_password", "")

    if not all([to_email, sender_email, sender_password]):
        return

    sent_log  = _load_json(SENT_LOG_FILE, {})
    today     = date.today()
    title     = schedule_data.get("curriculum_title", "Curriculum")

    for sem in schedule_data.get("semesters", []):
        sem_num        = str(sem.get("semester_number", ""))
        start_date_str = sem.get("start_date", "")
        if not start_date_str:
            continue

        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            continue

        days_until = (start_date - today).days

        for trigger_key, days in [("3_days", 3), ("1_day", 1), ("on_day", 0)]:
            if days_until != days:
                continue
            log_key = f"sem_{sem_num}_{trigger_key}"
            if sent_log.get(log_key):
                continue

            subject = _build_subject(title, sem_num, sem.get("semester_title", ""),
                                     trigger_key, days_until)
            body    = _build_email_body(schedule_data, sem, days_until, trigger_key)

            try:
                _send_email(to_email, sender_email, sender_password, subject, body)
                sent_log[log_key] = datetime.now().isoformat()
                _save_json(SENT_LOG_FILE, sent_log)
                print(f"[ReminderScheduler] ✅ Sent: {log_key} → {to_email}")
            except Exception as e:
                print(f"[ReminderScheduler] ❌ Failed {log_key}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _build_subject(title, sem_num, sem_title, trigger_key, days_until):
    if trigger_key == "on_day":
        return f"🎓 TODAY: Semester {sem_num} of '{title}' starts now!"
    elif days_until == 1:
        return f"⏰ TOMORROW: Semester {sem_num} — {sem_title}"
    else:
        return f"📅 {days_until} days left: Semester {sem_num} — {sem_title}"


def _build_email_body(schedule_data, sem, days_until, trigger):
    title     = schedule_data.get("curriculum_title", "Your Curriculum")
    level     = schedule_data.get("level", "")
    sem_num   = sem.get("semester_number", "")
    sem_title = sem.get("semester_title", "")
    sem_date  = sem.get("start_date", "")
    courses   = sem.get("courses", [])

    if trigger == "on_day":
        headline = f"🎓 Semester {sem_num} starts TODAY!"
        intro    = f"Today is the first day of Semester {sem_num}: {sem_title}."
    elif days_until == 1:
        headline = f"⏰ Semester {sem_num} starts TOMORROW!"
        intro    = f"Just 1 day left before Semester {sem_num}: {sem_title} begins."
    else:
        headline = f"📅 Semester {sem_num} starts in {days_until} days!"
        intro    = f"You have {days_until} days to prepare for Semester {sem_num}: {sem_title}."

    lines = [
        headline, "=" * 55, "",
        f"📚 Curriculum : {title}",
        f"🎓 Level      : {level}",
        f"📋 Semester   : {sem_num} — {sem_title}",
        f"📅 Start Date : {sem_date}",
        "", intro, "",
        "─" * 55,
        f"📖 Courses in Semester {sem_num}:",
        "─" * 55,
    ]

    for c in courses:
        lines.append(f"\n  • [{c.get('course_code','')}] {c.get('course_name','')}")
        lines.append(f"    Credits: {c.get('credits','4')}  |  Hours/week: {c.get('hours_per_week','3')}")
        topics = c.get("topics", [])
        if topics:
            lines.append(f"    Topics : {', '.join(topics[:4])}")

    lines += [
        "", "─" * 55,
        "💡 Preparation Tips:",
        "  ✓ Review topics from the previous semester",
        "  ✓ Set up your study schedule for the week",
        "  ✓ Gather study materials for the new courses",
        "", "=" * 55,
        "Sent by CurricuForge — AI-Powered Curriculum Design",
        f"Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        "=" * 55,
    ]

    return "\n".join(lines)


def _send_email(to_email, sender_email, sender_password, subject, body):
    msg = MIMEMultipart()
    msg["From"]    = sender_email
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)