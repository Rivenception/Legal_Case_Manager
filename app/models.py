from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def now_utc():
    return datetime.now(timezone.utc)


entry_people = db.Table(
    "entry_people",
    db.Column("entry_id", db.Integer, db.ForeignKey("timeline_entries.id"), primary_key=True),
    db.Column("person_id", db.Integer, db.ForeignKey("people.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Person(db.Model):
    __tablename__ = "people"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(120))
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=now_utc)

    entries = db.relationship(
        "TimelineEntry", secondary=entry_people, back_populates="people",
        order_by="TimelineEntry.occurred_at.desc()",
    )

    def __repr__(self):
        return f"<Person {self.name}>"


class TimelineEntry(db.Model):
    __tablename__ = "timeline_entries"

    id = db.Column(db.Integer, primary_key=True)
    occurred_at = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(120))

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])

    people = db.relationship(
        "Person", secondary=entry_people, back_populates="entries",
        order_by="Person.name",
    )
    evidence = db.relationship(
        "Evidence", back_populates="timeline_entry",
        order_by="Evidence.uploaded_at",
    )

    def __repr__(self):
        return f"<TimelineEntry {self.id} {self.occurred_at}>"


class Evidence(db.Model):
    __tablename__ = "evidence"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # name stored on disk
    original_filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    tags = db.Column(db.String(255), default="")

    timeline_entry_id = db.Column(db.Integer, db.ForeignKey("timeline_entries.id"))
    timeline_entry = db.relationship("TimelineEntry", back_populates="evidence")

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_by = db.relationship("User")
    uploaded_at = db.Column(db.DateTime, default=now_utc)

    def __repr__(self):
        return f"<Evidence {self.original_filename}>"


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date)
    done = db.Column(db.Boolean, default=False, nullable=False)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_by = db.relationship("User")
    created_at = db.Column(db.DateTime, default=now_utc)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Task {self.id} {self.description[:20]!r}>"
