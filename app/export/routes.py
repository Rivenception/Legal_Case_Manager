from datetime import datetime

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models import TimelineEntry

export_bp = Blueprint("export", __name__, url_prefix="/export")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


@export_bp.route("/report")
@login_required
def report():
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    query = TimelineEntry.query
    dt_from = _parse_date(date_from)
    dt_to = _parse_date(date_to)
    if dt_from:
        query = query.filter(TimelineEntry.occurred_at >= dt_from)
    if dt_to:
        query = query.filter(TimelineEntry.occurred_at <= dt_to)

    entries = query.order_by(TimelineEntry.occurred_at.asc()).all()

    return render_template(
        "export/report.html",
        entries=entries,
        date_from=date_from,
        date_to=date_to,
        generated_at=datetime.now(),
    )
