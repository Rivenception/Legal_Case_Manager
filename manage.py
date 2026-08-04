import getpass

import click
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import User

FTS_STATEMENTS = [
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS timeline_fts USING fts5(
        description, content='timeline_entries', content_rowid='id'
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS timeline_fts_ai AFTER INSERT ON timeline_entries BEGIN
        INSERT INTO timeline_fts(rowid, description) VALUES (new.id, new.description);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS timeline_fts_ad AFTER DELETE ON timeline_entries BEGIN
        INSERT INTO timeline_fts(timeline_fts, rowid, description) VALUES('delete', old.id, old.description);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS timeline_fts_au AFTER UPDATE ON timeline_entries BEGIN
        INSERT INTO timeline_fts(timeline_fts, rowid, description) VALUES('delete', old.id, old.description);
        INSERT INTO timeline_fts(rowid, description) VALUES (new.id, new.description);
    END
    """,
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS person_fts USING fts5(
        name, notes, content='people', content_rowid='id'
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS person_fts_ai AFTER INSERT ON people BEGIN
        INSERT INTO person_fts(rowid, name, notes) VALUES (new.id, new.name, new.notes);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS person_fts_ad AFTER DELETE ON people BEGIN
        INSERT INTO person_fts(person_fts, rowid, name, notes) VALUES('delete', old.id, old.name, old.notes);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS person_fts_au AFTER UPDATE ON people BEGIN
        INSERT INTO person_fts(person_fts, rowid, name, notes) VALUES('delete', old.id, old.name, old.notes);
        INSERT INTO person_fts(rowid, name, notes) VALUES (new.id, new.name, new.notes);
    END
    """,
]


@click.group()
def cli():
    """Management commands for the Family Case Tracker."""


def _ensure_user_columns():
    cols = {row[1] for row in db.session.execute(text("PRAGMA table_info(users)")).fetchall()}
    if "email" not in cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
    if "is_admin" not in cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
    db.session.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email) WHERE email IS NOT NULL")
    )
    db.session.commit()


@cli.command("init-db")
def init_db():
    """Create all tables, apply schema updates, and set up full-text search indexes."""
    app = create_app()
    with app.app_context():
        db.create_all()
        _ensure_user_columns()
        for stmt in FTS_STATEMENTS:
            db.session.execute(text(stmt))
        db.session.commit()
    click.echo("Database initialized.")


@cli.command("create-user")
@click.argument("username")
def create_user(username):
    """Create a new user account (prompts for password)."""
    app = create_app()
    with app.app_context():
        if User.query.filter_by(username=username).first():
            click.echo(f"User '{username}' already exists.")
            return
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            click.echo("Passwords do not match.")
            return
        if len(password) < 8:
            click.echo("Password must be at least 8 characters.")
            return
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"User '{username}' created.")


@cli.command("list-users")
def list_users():
    """List all user accounts."""
    app = create_app()
    with app.app_context():
        for user in User.query.order_by(User.username).all():
            admin_flag = " [admin]" if user.is_admin else ""
            click.echo(f"{user.id}\t{user.username}{admin_flag}\t{user.email or '(no email)'}\tcreated {user.created_at}")


@cli.command("delete-user")
@click.argument("username")
def delete_user(username):
    """Delete a user account by username."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User '{username}' not found.")
            return
        db.session.delete(user)
        db.session.commit()
        click.echo(f"User '{username}' deleted.")


@cli.command("change-password")
@click.argument("username")
def change_password(username):
    """Change a user's password."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User '{username}' not found.")
            return
        password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            click.echo("Passwords do not match.")
            return
        if len(password) < 8:
            click.echo("Password must be at least 8 characters.")
            return
        user.set_password(password)
        db.session.commit()
        click.echo(f"Password updated for '{username}'.")


@cli.command("make-admin")
@click.argument("username")
def make_admin(username):
    """Grant a user admin privileges."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User '{username}' not found.")
            return
        user.is_admin = True
        db.session.commit()
        click.echo(f"'{username}' is now an admin.")


@cli.command("revoke-admin")
@click.argument("username")
def revoke_admin(username):
    """Remove a user's admin privileges."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User '{username}' not found.")
            return
        user.is_admin = False
        db.session.commit()
        click.echo(f"'{username}' is no longer an admin.")


@cli.command("set-email")
@click.argument("username")
@click.argument("email")
def set_email(username, email):
    """Set (or update) a user's email address, used for password reset."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f"User '{username}' not found.")
            return
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            click.echo(f"Email '{email}' is already used by '{existing.username}'.")
            return
        user.email = email
        db.session.commit()
        click.echo(f"Email for '{username}' set to {email}.")


if __name__ == "__main__":
    cli()
