from datetime import datetime, date

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Task, now_utc

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@tasks_bp.route("/")
@login_required
def list_tasks():
    show_done = request.args.get("show_done") == "1"
    query = Task.query
    if not show_done:
        query = query.filter_by(done=False)
    items = query.order_by(Task.done, Task.due_date.is_(None), Task.due_date.asc()).all()
    return render_template("tasks/list.html", items=items, show_done=show_done, today=date.today())


@tasks_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_task():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        if not description:
            flash("Description is required.", "error")
        else:
            task = Task(
                description=description,
                due_date=_parse_date(request.form.get("due_date")),
                created_by_id=current_user.id,
            )
            db.session.add(task)
            db.session.commit()
            flash("Task added.", "success")
            return redirect(url_for("tasks.list_tasks"))

    return render_template("tasks/form.html", task=None)


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = db.session.get(Task, task_id) or abort(404)

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        if not description:
            flash("Description is required.", "error")
        else:
            task.description = description
            task.due_date = _parse_date(request.form.get("due_date"))
            db.session.commit()
            flash("Task updated.", "success")
            return redirect(url_for("tasks.list_tasks"))

    return render_template("tasks/form.html", task=task)


@tasks_bp.route("/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    task.done = not task.done
    task.completed_at = now_utc() if task.done else None
    db.session.commit()
    return redirect(request.referrer or url_for("tasks.list_tasks"))


@tasks_bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = db.session.get(Task, task_id) or abort(404)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("tasks.list_tasks"))
