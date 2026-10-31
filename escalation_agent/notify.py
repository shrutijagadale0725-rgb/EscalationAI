"""Pluggable notifications. Every channel is optional and can never break a case."""
import logging
import os
import smtplib
import threading
import urllib.request
from email.message import EmailMessage
from pathlib import Path

log = logging.getLogger(__name__)


def _load_env():
    """Load NTFY_/SMTP_/NOTIFY_ settings from agent/.env (never overrides real env vars)."""
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith(("NTFY_", "SMTP_", "NOTIFY_")):
            os.environ.setdefault(key, val.strip().strip('"').strip("'"))


_load_env()


def _ntfy(title, message):
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        return
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"),
                                 headers={"Title": title}, method="POST")
    urllib.request.urlopen(req, timeout=5).close()


def _email(title, message, to):
    user, pwd = os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    to = to or os.getenv("NOTIFY_EMAIL_TO")
    if not (user and pwd and to):
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = title, user, to
    msg.set_content(message)
    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST", "smtp.gmail.com"), 465, timeout=10) as s:
        s.login(user, pwd.replace(" ", ""))
        s.send_message(msg)


def _send_all(title, message, email):
    for send in (lambda: _ntfy(title, message), lambda: _email(title, message, email)):
        try:
            send()
        except Exception as e:
            log.warning("notification failed: %s", e)


def notify(title, message, email=None):
    if os.getenv("PYTEST_CURRENT_TEST"):  # tests never send real messages
        return
    threading.Thread(target=_send_all, args=(title, message, email), daemon=True).start()