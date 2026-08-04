import smtplib
from email.message import EmailMessage

from flask import current_app


def is_mail_configured():
    return bool(current_app.config.get("MAIL_SERVER") and current_app.config.get("MAIL_FROM"))


def send_email(to_addr, subject, body):
    """Send a plain-text email. Returns True if sent, False if mail isn't configured."""
    if not is_mail_configured():
        current_app.logger.warning("MAIL_SERVER not configured; skipping email to %s", to_addr)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config["MAIL_FROM"]
    msg["To"] = to_addr
    msg.set_content(body)

    host = current_app.config["MAIL_SERVER"]
    port = current_app.config["MAIL_PORT"]
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    use_tls = current_app.config.get("MAIL_USE_TLS", True)

    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)
    return True
