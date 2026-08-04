import re

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import text

from app.extensions import db
from app.models import TimelineEntry, Person

search_bp = Blueprint("search", __name__, url_prefix="/search")


def _build_match_query(raw_query):
    tokens = re.findall(r"\w+", raw_query)
    if not tokens:
        return None
    return " AND ".join(f"{t}*" for t in tokens)


@search_bp.route("/")
@login_required
def search():
    raw_query = request.args.get("q", "").strip()
    entries = []
    people = []

    match_query = _build_match_query(raw_query) if raw_query else None

    if match_query:
        entry_rows = db.session.execute(
            text(
                """
                SELECT timeline_entries.id AS id
                FROM timeline_entries
                JOIN timeline_fts ON timeline_fts.rowid = timeline_entries.id
                WHERE timeline_fts MATCH :q
                ORDER BY rank
                """
            ),
            {"q": match_query},
        ).all()
        entry_ids = [row.id for row in entry_rows]
        if entry_ids:
            entries_by_id = {e.id: e for e in TimelineEntry.query.filter(TimelineEntry.id.in_(entry_ids)).all()}
            entries = [entries_by_id[i] for i in entry_ids if i in entries_by_id]

        person_rows = db.session.execute(
            text(
                """
                SELECT people.id AS id
                FROM people
                JOIN person_fts ON person_fts.rowid = people.id
                WHERE person_fts MATCH :q
                ORDER BY rank
                """
            ),
            {"q": match_query},
        ).all()
        person_ids = [row.id for row in person_rows]
        if person_ids:
            people_by_id = {p.id: p for p in Person.query.filter(Person.id.in_(person_ids)).all()}
            people = [people_by_id[i] for i in person_ids if i in people_by_id]

    return render_template("search/results.html", query=raw_query, entries=entries, people=people)
