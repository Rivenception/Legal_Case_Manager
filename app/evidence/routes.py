import io
import os
import uuid
import zipfile

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
    current_app, send_from_directory, send_file,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Evidence, TimelineEntry

evidence_bp = Blueprint("evidence", __name__, url_prefix="/evidence")


def _allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@evidence_bp.route("/")
@login_required
def list_evidence():
    tag = request.args.get("tag", "").strip()
    query = Evidence.query
    if tag:
        query = query.filter(Evidence.tags.ilike(f"%{tag}%"))
    items = query.order_by(Evidence.uploaded_at.desc()).all()
    return render_template("evidence/list.html", items=items, tag=tag)


@evidence_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    entries = TimelineEntry.query.order_by(TimelineEntry.occurred_at.desc()).all()
    preselected_entry_id = request.args.get("entry_id", type=int)

    if request.method == "POST":
        files = [f for f in request.files.getlist("file") if f and f.filename]
        if not files:
            flash("Please choose at least one file to upload.", "error")
            return render_template("evidence/form.html", entries=entries, preselected_entry_id=preselected_entry_id)

        entry_id = request.form.get("entry_id", type=int)
        description = request.form.get("description", "").strip()
        tags = request.form.get("tags", "").strip()

        uploaded_count = 0
        skipped = []

        for file in files:
            if not _allowed_file(file.filename):
                skipped.append(file.filename)
                continue

            original_filename = secure_filename(file.filename)
            ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
            stored_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name))

            evidence = Evidence(
                filename=stored_name,
                original_filename=original_filename,
                description=description,
                tags=tags,
                timeline_entry_id=entry_id or None,
                uploaded_by_id=current_user.id,
            )
            db.session.add(evidence)
            uploaded_count += 1

        if uploaded_count:
            db.session.commit()
            flash(f"Uploaded {uploaded_count} file(s).", "success")
        if skipped:
            flash(f"Skipped {len(skipped)} file(s) with disallowed type: {', '.join(skipped)}", "error")

        if not uploaded_count:
            return render_template("evidence/form.html", entries=entries, preselected_entry_id=preselected_entry_id)

        if entry_id:
            return redirect(url_for("timeline.view_entry", entry_id=entry_id))
        return redirect(url_for("evidence.list_evidence"))

    return render_template("evidence/form.html", entries=entries, preselected_entry_id=preselected_entry_id)


@evidence_bp.route("/<int:evidence_id>/download")
@login_required
def download(evidence_id):
    ev = db.session.get(Evidence, evidence_id) or abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], ev.filename,
        download_name=ev.original_filename,
    )


@evidence_bp.route("/entry/<int:entry_id>/download-all")
@login_required
def download_all_for_entry(entry_id):
    entry = db.session.get(TimelineEntry, entry_id) or abort(404)
    if not entry.evidence:
        abort(404)

    buffer = io.BytesIO()
    used_names = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for ev in entry.evidence:
            path = os.path.join(current_app.config["UPLOAD_FOLDER"], ev.filename)
            if not os.path.exists(path):
                continue
            arcname = ev.original_filename
            base, ext = os.path.splitext(arcname)
            counter = 1
            while arcname in used_names:
                arcname = f"{base} ({counter}){ext}"
                counter += 1
            used_names.add(arcname)
            zf.write(path, arcname=arcname)
    buffer.seek(0)

    zip_name = f"evidence_{entry.occurred_at.strftime('%Y-%m-%d')}_entry{entry.id}.zip"
    return send_file(buffer, mimetype="application/zip", as_attachment=True, download_name=zip_name)


@evidence_bp.route("/<int:evidence_id>/delete", methods=["POST"])
@login_required
def delete_evidence(evidence_id):
    ev = db.session.get(Evidence, evidence_id) or abort(404)
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], ev.filename)
    entry_id = ev.timeline_entry_id
    db.session.delete(ev)
    db.session.commit()
    if os.path.exists(file_path):
        os.remove(file_path)
    flash("Evidence deleted.", "info")
    if entry_id:
        return redirect(url_for("timeline.view_entry", entry_id=entry_id))
    return redirect(url_for("evidence.list_evidence"))
