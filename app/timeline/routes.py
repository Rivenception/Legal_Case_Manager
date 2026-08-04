from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import TimelineEntry, Person, Evidence, now_utc

timeline_bp = Blueprint("timeline", __name__, url_prefix="/timeline")


def _parse_datetime(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@timeline_bp.route("/")
@login_required
def list_entries():
    query = TimelineEntry.query

    person_id = request.args.get("person_id", type=int)
    category = request.args.get("category", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    if person_id:
        query = query.filter(TimelineEntry.people.any(Person.id == person_id))
    if category:
        query = query.filter(TimelineEntry.category == category)
    if date_from:
        dt = _parse_datetime(date_from)
        if dt:
            query = query.filter(TimelineEntry.occurred_at >= dt)
    if date_to:
        dt = _parse_datetime(date_to)
        if dt:
            query = query.filter(TimelineEntry.occurred_at <= dt)

    entries = query.order_by(TimelineEntry.occurred_at.desc()).all()

    people = Person.query.order_by(Person.name).all()
    categories = [
        row[0] for row in
        db.session.query(TimelineEntry.category).filter(TimelineEntry.category.isnot(None)).distinct()
        if row[0]
    ]

    return render_template(
        "timeline/list.html",
        entries=entries,
        people=people,
        categories=sorted(categories),
        filters={
            "person_id": person_id,
            "category": category,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@timeline_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_entry():
    people = Person.query.order_by(Person.name).all()
    standalone_evidence = Evidence.query.filter_by(timeline_entry_id=None).order_by(Evidence.uploaded_at.desc()).all()

    if request.method == "POST":
        occurred_at = _parse_datetime(request.form.get("occurred_at"))
        description = request.form.get("description", "").strip()

        if not occurred_at or not description:
            flash("Date/time and description are required.", "error")
        else:
            entry = TimelineEntry(
                occurred_at=occurred_at,
                description=description,
                category=request.form.get("category", "").strip() or None,
                created_by_id=current_user.id,
            )
            person_ids = request.form.getlist("people")
            if person_ids:
                entry.people = Person.query.filter(Person.id.in_(person_ids)).all()

            evidence_ids = request.form.getlist("link_evidence")
            db.session.add(entry)
            db.session.flush()
            if evidence_ids:
                Evidence.query.filter(Evidence.id.in_(evidence_ids)).update(
                    {Evidence.timeline_entry_id: entry.id}, synchronize_session=False
                )
            db.session.commit()
            flash("Timeline entry added.", "success")
            return redirect(url_for("timeline.view_entry", entry_id=entry.id))

    return render_template(
        "timeline/form.html", entry=None, people=people, standalone_evidence=standalone_evidence
    )


@timeline_bp.route("/<int:entry_id>")
@login_required
def view_entry(entry_id):
    entry = db.session.get(TimelineEntry, entry_id) or abort(404)
    return render_template("timeline/detail.html", entry=entry)


@timeline_bp.route("/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(entry_id):
    entry = db.session.get(TimelineEntry, entry_id) or abort(404)
    people = Person.query.order_by(Person.name).all()
    standalone_evidence = Evidence.query.filter(
        (Evidence.timeline_entry_id == None) | (Evidence.timeline_entry_id == entry.id)  # noqa: E711
    ).order_by(Evidence.uploaded_at.desc()).all()

    if request.method == "POST":
        occurred_at = _parse_datetime(request.form.get("occurred_at"))
        description = request.form.get("description", "").strip()

        if not occurred_at or not description:
            flash("Date/time and description are required.", "error")
        else:
            entry.occurred_at = occurred_at
            entry.description = description
            entry.category = request.form.get("category", "").strip() or None

            person_ids = request.form.getlist("people")
            entry.people = Person.query.filter(Person.id.in_(person_ids)).all() if person_ids else []

            evidence_ids = set(request.form.getlist("link_evidence"))
            for ev in list(entry.evidence):
                if str(ev.id) not in evidence_ids:
                    ev.timeline_entry_id = None
            if evidence_ids:
                Evidence.query.filter(Evidence.id.in_(evidence_ids)).update(
                    {Evidence.timeline_entry_id: entry.id}, synchronize_session=False
                )

            entry.updated_by_id = current_user.id
            entry.updated_at = now_utc()
            db.session.commit()
            flash("Timeline entry updated.", "success")
            return redirect(url_for("timeline.view_entry", entry_id=entry.id))

    return render_template(
        "timeline/form.html", entry=entry, people=people, standalone_evidence=standalone_evidence
    )


@timeline_bp.route("/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id):
    entry = db.session.get(TimelineEntry, entry_id) or abort(404)
    for ev in list(entry.evidence):
        ev.timeline_entry_id = None
    db.session.delete(entry)
    db.session.commit()
    flash("Timeline entry deleted.", "info")
    return redirect(url_for("timeline.list_entries"))
