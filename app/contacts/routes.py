from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required

from app.extensions import db
from app.models import Person

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")


@contacts_bp.route("/")
@login_required
def list_people():
    people = Person.query.order_by(Person.name).all()
    return render_template("contacts/list.html", people=people)


@contacts_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_person():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "error")
        else:
            person = Person(
                name=name,
                role=request.form.get("role", "").strip() or None,
                notes=request.form.get("notes", "").strip(),
            )
            db.session.add(person)
            db.session.commit()
            flash("Contact added.", "success")
            return redirect(url_for("contacts.view_person", person_id=person.id))

    return render_template("contacts/form.html", person=None)


@contacts_bp.route("/<int:person_id>")
@login_required
def view_person(person_id):
    person = db.session.get(Person, person_id) or abort(404)
    return render_template("contacts/detail.html", person=person)


@contacts_bp.route("/<int:person_id>/edit", methods=["GET", "POST"])
@login_required
def edit_person(person_id):
    person = db.session.get(Person, person_id) or abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "error")
        else:
            person.name = name
            person.role = request.form.get("role", "").strip() or None
            person.notes = request.form.get("notes", "").strip()
            db.session.commit()
            flash("Contact updated.", "success")
            return redirect(url_for("contacts.view_person", person_id=person.id))

    return render_template("contacts/form.html", person=person)


@contacts_bp.route("/<int:person_id>/delete", methods=["POST"])
@login_required
def delete_person(person_id):
    person = db.session.get(Person, person_id) or abort(404)
    db.session.delete(person)
    db.session.commit()
    flash("Contact deleted.", "info")
    return redirect(url_for("contacts.list_people"))
