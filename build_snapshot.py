"""
Builds a standalone, read-only "case snapshot" executable — bundles the app
plus a copy of the CURRENT contents of instance/ (database + evidence files)
into a single .exe that someone else can double-click to browse the case
data, with all editing disabled.

Run this any time you want a fresh snapshot to share:

    .\\venv\\Scripts\\python.exe build_snapshot.py

Output goes to snapshot_dist/. This does NOT touch your live instance/ data
— it only reads from it to build a copy.
"""
import os
import secrets
import shutil
import subprocess
import sys
from datetime import date

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LIVE_INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
STAGING_DIR = os.path.join(BASE_DIR, "_snapshot_build")
STAGED_INSTANCE_DIR = os.path.join(STAGING_DIR, "instance")
DIST_DIR = os.path.join(BASE_DIR, "snapshot_dist")

READONLY_USERNAME = "Read_Only"


def stage_instance_copy():
    if os.path.exists(STAGING_DIR):
        shutil.rmtree(STAGING_DIR)
    os.makedirs(STAGING_DIR)

    if not os.path.exists(os.path.join(LIVE_INSTANCE_DIR, "case_tracker.db")):
        print("ERROR: instance/case_tracker.db not found. Run 'python manage.py init-db' first.")
        sys.exit(1)

    shutil.copytree(
        LIVE_INSTANCE_DIR, STAGED_INSTANCE_DIR,
        ignore=shutil.ignore_patterns("secret_key.txt"),
    )

    # Fresh secret key dedicated to this snapshot build — never reuse the
    # live server's key in something that leaves the house.
    with open(os.path.join(STAGED_INSTANCE_DIR, "secret_key.txt"), "w") as f:
        f.write(secrets.token_hex(32))

    build_date = date.today().isoformat()
    with open(os.path.join(STAGED_INSTANCE_DIR, "SNAPSHOT_BUILT_AT"), "w") as f:
        f.write(build_date)

    return build_date


def prepare_snapshot_database():
    """Scrub real users' password hashes and (re)create the Read_Only account
    in the STAGED database copy only. Never touches the live database."""
    os.environ["CASE_TRACKER_INSTANCE_DIR"] = STAGED_INSTANCE_DIR
    os.environ.pop("SNAPSHOT_MODE", None)

    sys.path.insert(0, BASE_DIR)
    from app import create_app
    from app.extensions import db
    from app.models import User

    app = create_app()
    with app.app_context():
        for user in User.query.filter(User.username != READONLY_USERNAME).all():
            user.password_hash = "disabled-in-snapshot"

        reviewer = User.query.filter_by(username=READONLY_USERNAME).first()
        password = secrets.token_urlsafe(9)
        if not reviewer:
            reviewer = User(username=READONLY_USERNAME, is_admin=False, email=None)
            db.session.add(reviewer)
        reviewer.set_password(password)
        reviewer.is_admin = False

        db.session.commit()

    return password


def run_pyinstaller(build_date):
    exe_name = f"CaseTracker_Snapshot_{build_date}"
    work_dir = os.path.join(STAGING_DIR, "pyinstaller_work")
    spec_dir = os.path.join(STAGING_DIR, "spec")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", exe_name,
        "--distpath", DIST_DIR,
        "--workpath", work_dir,
        "--specpath", spec_dir,
        "--add-data", f"{os.path.join(BASE_DIR, 'app', 'templates')};app/templates",
        "--add-data", f"{os.path.join(BASE_DIR, 'app', 'static')};app/static",
        "--add-data", f"{STAGED_INSTANCE_DIR};instance",
        os.path.join(BASE_DIR, "snapshot_main.py"),
    ]
    subprocess.run(cmd, check=True, cwd=BASE_DIR)
    return os.path.join(DIST_DIR, exe_name + ".exe")


def write_credentials_file(exe_path, password, build_date):
    creds_path = os.path.join(DIST_DIR, f"README_login_{build_date}.txt")
    with open(creds_path, "w", encoding="utf-8") as f:
        f.write(
            "Family Case Tracker — read-only snapshot\n"
            "=========================================\n\n"
            f"Double-click {os.path.basename(exe_path)} to open it.\n"
            "It will start a small local program on your own computer and\n"
            "open your web browser to it automatically.\n\n"
            "Log in with:\n"
            f"  Username: {READONLY_USERNAME}\n"
            f"  Password: {password}\n\n"
            "This copy is view/download only — nothing can be added, edited,\n"
            "or deleted. Close the black console window when you're done to\n"
            "stop the program.\n\n"
            "Windows may show a security warning since this program isn't\n"
            "digitally signed. Choose \"More info\" then \"Run anyway\".\n"
        )
    return creds_path


def main():
    print("Staging a copy of instance/ ...")
    build_date = stage_instance_copy()

    print("Preparing the Read_Only account in the snapshot database...")
    password = prepare_snapshot_database()

    print("Running PyInstaller (this can take a minute or two)...")
    exe_path = run_pyinstaller(build_date)

    creds_path = write_credentials_file(exe_path, password, build_date)

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)

    print()
    print("=" * 60)
    print("Done.")
    print(f"Executable:  {exe_path}")
    print(f"Login info:  {creds_path}")
    print(f"Size:        {size_mb:.0f} MB")
    if size_mb > 20:
        print()
        print("NOTE: most email providers cap attachments around 20-25 MB.")
        print("Share this via a private cloud folder / file-transfer link")
        print("instead of a direct email attachment.")
    print("=" * 60)


if __name__ == "__main__":
    main()
