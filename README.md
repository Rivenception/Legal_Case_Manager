# Family Case Tracker

A private, self-hosted case management app for tracking evidence, facts, contacts,
and deadlines related to an ongoing dispute. Runs entirely on one computer on your
home network — nothing is sent to the cloud.

## Features

- **Timeline** — chronological log of facts/events, taggable with people and category, with linked evidence
- **Evidence** — upload photos, PDFs, videos, screenshots (single or multiple files at once); link to a timeline
  entry or keep standalone; download any file individually, or download all evidence for a timeline entry as a zip
- **Contacts** — people involved (neighbors, witnesses, officers, mediators) with free-text notes
- **Tasks** — simple due-date tracker with overdue highlighting
- **Search** — full-text search across timeline entries and contact notes (SQLite FTS5)
- **Export** — printable HTML report of the full timeline (use your browser's Print → Save as PDF)
- **Admin & password reset** — admin users can view all accounts and set/edit emails; any user can reset a
  forgotten password via an emailed link (requires SMTP setup, see below)

## Requirements

- Python 3.10+
- No external database — uses a local SQLite file

## Setup

All commands below assume you're in the `Legal_Case_Manager` project folder.

### 1. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your prompt once it's active.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize the database

```bash
python manage.py init-db
```

This creates `instance/case_tracker.db` with all tables and search indexes.
The `instance/` folder (database + uploaded evidence) is excluded from Git via
`.gitignore` — it's personal, sensitive data and should never be committed.

`init-db` is safe to re-run any time (e.g. after pulling app updates) — it also applies
any new schema changes to your existing database without touching your data.

### 4. Create user accounts

Create one account per family member who needs access (2-3 recommended):

```bash
python manage.py create-user alice
python manage.py create-user bob
```

You'll be prompted to set a password for each (typed input is hidden).

Other account management commands:
```bash
python manage.py list-users
python manage.py change-password alice
python manage.py delete-user bob
python manage.py make-admin alice
python manage.py revoke-admin alice
python manage.py set-email alice alice@example.com
```

Admins can also manage emails and admin status for any account from the app itself,
under the **Admin** nav link (visible only to admins) once logged in.

### 5. (Optional) Set up email for password resets

Users can reset a forgotten password via an emailed link, but this requires SMTP
credentials so the app can actually send mail. Without this set up, the app still
works fine for everything else — "forgot password" just won't be able to send an email
(the reset link is written to the server console instead, which an admin can pass along
manually if needed).

To enable it, copy `.env.example` to `.env` in the project root and fill in your SMTP
details (the example file has step-by-step instructions for Gmail app passwords).
`.env` is gitignored and never committed. Restart the server after editing it.

### 6. Run the server

```bash
python run.py
```

The app is now running on port 5000.

- On the same computer: open **http://localhost:5000**
- On another device (phone, tablet, laptop) on the same Wi-Fi/network: open
  **http://<this-computer's-local-IP>:5000** (see below for how to find it)

## Finding your computer's local IP address

**Windows (PowerShell):**
```powershell
ipconfig
```
Look for the "IPv4 Address" under your active adapter (Wi-Fi or Ethernet), e.g. `192.168.1.42`.

**macOS:**
```bash
ipconfig getifaddr en0
```

**Linux:**
```bash
hostname -I
```

Then, from any phone or computer connected to the *same* home network, visit:
```
http://192.168.1.42:5000
```
(substituting your own IP). This is not exposed to the public internet — it only
works for devices on your local network.

## Project structure

```
Legal_Case_Manager/
├── app/
│   ├── auth/          # login/logout/forgot-password/reset-password
│   ├── admin/         # user list + edit (email, admin flag)
│   ├── main/          # dashboard
│   ├── timeline/       # fact timeline CRUD
│   ├── contacts/       # people CRUD
│   ├── evidence/       # file upload/download, zip download
│   ├── tasks/          # deadline tracker
│   ├── search/         # full-text search
│   ├── export/         # printable report
│   ├── templates/
│   ├── static/css/
│   ├── models.py
│   ├── mail.py          # SMTP sending for password-reset emails
│   └── extensions.py
├── instance/            # SQLite DB + uploaded evidence (gitignored)
├── config.py
├── manage.py             # CLI: init-db, create-user, make-admin, etc.
├── run.py                # start the server
├── .env.example          # copy to .env for SMTP/password-reset setup
└── requirements.txt
```

## Notes on privacy

- All data (database + uploaded files) lives under `instance/`, which is excluded from Git.
- Do not deploy this to a public server or port-forward it to the internet — it's designed
  for trusted use on a private home network only.
- All logged-in users see the same shared case data; there's no per-user data isolation,
  only an "added by" / "last edited by" note on each entry.
- Admins (see `make-admin` above) can see every account's username and email under the
  Admin page — grant admin only to accounts that should have that visibility.
- SMTP credentials in `.env` (if configured) can send email as that account — treat them
  like a password and never commit `.env`.

## Local Access
http://192.168.0.4:5000
http://127.0.0.1:5000