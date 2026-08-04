import os
import sys

from flask import Flask, abort, request
from flask_login import current_user

from config import Config
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    if getattr(sys, "frozen", False):
        # Flask's automatic template/static folder detection relies on
        # module __file__ paths that PyInstaller doesn't lay out normally.
        base = sys._MEIPASS
        app = Flask(
            __name__,
            template_folder=os.path.join(base, "app", "templates"),
            static_folder=os.path.join(base, "app", "static"),
        )
    else:
        app = Flask(__name__, instance_relative_config=False)

    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    if app.config.get("SNAPSHOT_MODE"):
        @app.before_request
        def block_writes_in_snapshot_mode():
            # Login itself must stay allowed (it's a POST, but the user isn't
            # authenticated yet) — everything else mutating is blocked once
            # a session exists.
            if current_user.is_authenticated and request.method not in ("GET", "HEAD", "OPTIONS"):
                abort(403, description="This is a read-only case snapshot. Editing is disabled.")

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.timeline.routes import timeline_bp
    from app.contacts.routes import contacts_bp
    from app.evidence.routes import evidence_bp
    from app.tasks.routes import tasks_bp
    from app.search.routes import search_bp
    from app.export.routes import export_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        from datetime import date
        snapshot_built_at = None
        if app.config.get("SNAPSHOT_MODE"):
            marker = os.path.join(app.config["UPLOAD_FOLDER"], "..", "SNAPSHOT_BUILT_AT")
            marker = os.path.normpath(marker)
            if os.path.exists(marker):
                with open(marker, "r") as f:
                    snapshot_built_at = f.read().strip()
        return {
            "today": date.today(),
            "snapshot_mode": app.config.get("SNAPSHOT_MODE", False),
            "snapshot_built_at": snapshot_built_at,
        }

    return app
