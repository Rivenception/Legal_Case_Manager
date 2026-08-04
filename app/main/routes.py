from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required

from app.models import TimelineEntry, Task, Person, Evidence

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    recent_entries = TimelineEntry.query.order_by(TimelineEntry.occurred_at.desc()).limit(5).all()
    upcoming_tasks = (
        Task.query.filter_by(done=False)
        .order_by(Task.due_date.is_(None), Task.due_date.asc())
        .limit(5)
        .all()
    )
    overdue_count = Task.query.filter(
        Task.done.is_(False), Task.due_date.isnot(None), Task.due_date < date.today()
    ).count()

    stats = {
        "entries": TimelineEntry.query.count(),
        "people": Person.query.count(),
        "evidence": Evidence.query.count(),
        "open_tasks": Task.query.filter_by(done=False).count(),
        "overdue_tasks": overdue_count,
    }

    return render_template(
        "main/index.html",
        recent_entries=recent_entries,
        upcoming_tasks=upcoming_tasks,
        stats=stats,
    )
