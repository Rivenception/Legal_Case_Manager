import os
import secrets
import sys

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    # Running as a PyInstaller-built executable — bundled files are
    # extracted to a temp dir at sys._MEIPASS, not laid out like the repo.
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Snapshot builds (see build_snapshot.py) point this at their own bundled
# copy of instance/ instead of the normal project-relative one.
INSTANCE_DIR = os.environ.get("CASE_TRACKER_INSTANCE_DIR") or os.path.join(BASE_DIR, "instance")
UPLOAD_DIR = os.path.join(INSTANCE_DIR, "uploads")

SNAPSHOT_MODE = os.environ.get("SNAPSHOT_MODE", "false").strip().lower() in ("1", "true", "yes")

if not getattr(sys, "frozen", False):
    load_dotenv(os.path.join(BASE_DIR, ".env"))

_SECRET_KEY_FILE = os.path.join(INSTANCE_DIR, "secret_key.txt")


def _get_or_create_secret_key():
    env_key = os.environ.get("FLASK_SECRET_KEY")
    if env_key:
        return env_key
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    if os.path.exists(_SECRET_KEY_FILE):
        with open(_SECRET_KEY_FILE, "r") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(_SECRET_KEY_FILE, "w") as f:
        f.write(key)
    return key


class Config:
    SECRET_KEY = _get_or_create_secret_key()
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "case_tracker.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = UPLOAD_DIR
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB per upload
    ALLOWED_EXTENSIONS = {
        "png", "jpg", "jpeg", "gif", "webp", "heic",
        "pdf", "doc", "docx", "txt",
        "mp4", "mov", "avi", "mkv",
        "mp3", "wav", "m4a",
    }

    SNAPSHOT_MODE = SNAPSHOT_MODE
    SNAPSHOT_READONLY_USERNAME = "Read_Only"

    # SMTP settings for "forgot password" emails. Leave MAIL_SERVER unset to
    # disable emailing (reset links will just be logged instead of sent).
    MAIL_SERVER = os.environ.get("MAIL_SERVER") or None
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").strip().lower() in ("1", "true", "yes")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME") or None
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or None
    MAIL_FROM = os.environ.get("MAIL_FROM") or os.environ.get("MAIL_USERNAME") or None
