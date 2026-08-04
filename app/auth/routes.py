from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.extensions import db
from app.mail import send_email
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

RESET_TOKEN_SALT = "password-reset"
RESET_TOKEN_MAX_AGE = 3600  # 1 hour


def _generate_reset_token(user):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(user.id, salt=RESET_TOKEN_SALT)


def _verify_reset_token(token, max_age=RESET_TOKEN_MAX_AGE):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        return serializer.loads(token, salt=RESET_TOKEN_SALT, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))

        flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        identifier = request.form.get("username_or_email", "").strip()
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.email:
            token = _generate_reset_token(user)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            body = (
                f"Hi {user.username},\n\n"
                "A password reset was requested for your Family Case Tracker account.\n"
                f"Click the link below to set a new password (valid for 1 hour):\n\n"
                f"{reset_url}\n\n"
                "If you didn't request this, you can safely ignore this email."
            )
            try:
                sent = send_email(user.email, "Password reset — Case Tracker", body)
                if not sent:
                    current_app.logger.info("Password reset link for %s: %s", user.username, reset_url)
            except Exception:
                current_app.logger.exception("Failed to send password reset email to %s", user.email)

        flash(
            "If that account exists and has an email on file, a reset link has been sent.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user_id = _verify_reset_token(token)
    if user_id is None:
        flash("That password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    user = db.session.get(User, user_id)
    if not user:
        flash("Account not found.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            user.set_password(password)
            db.session.commit()
            flash("Password updated. You can now log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html")
