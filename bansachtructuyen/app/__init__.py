import os

from flask import Flask

from app.config import Config
from app.extensions import csrf, db, migrate
from app.utils import format_vnd, status_badge_class


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.admin import admin_bp
    from app.store import store_bp

    app.register_blueprint(store_bp)
    app.register_blueprint(admin_bp)

    app.jinja_env.filters["vnd"] = format_vnd
    app.jinja_env.globals["status_badge"] = status_badge_class

    @app.context_processor
    def inject_globals():
        from app.cart import cart_count
        from app.forms import CSRFOnlyForm

        return {
            "cart_count": cart_count(),
            "csrf_form": CSRFOnlyForm(),
        }

    with app.app_context():
        from app import models  # noqa: F401
        from app.seed import seed_sample_data

        db.create_all()
        seed_sample_data()

    return app
