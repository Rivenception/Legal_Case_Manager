from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/users")
@admin_required
def list_users():
    users = User.query.order_by(User.username).all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id) or abort(404)

    if request.method == "POST":
        email = request.form.get("email", "").strip() or None
        is_admin = request.form.get("is_admin") == "on"

        if user.id == current_user.id and not is_admin:
            flash("You can't remove your own admin access.", "error")
        elif email and User.query.filter(User.email == email, User.id != user.id).first():
            flash("Another user already has that email.", "error")
        else:
            user.email = email
            user.is_admin = is_admin
            db.session.commit()
            flash("User updated.", "success")
            return redirect(url_for("admin.list_users"))

    return render_template("admin/edit_user.html", user=user)
