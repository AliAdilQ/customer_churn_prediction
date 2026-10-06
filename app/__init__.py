"""Flask application factory and shared presentation helpers."""

import os
from pathlib import Path

from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

from config import BASE_DIR, Config
from .extensions import csrf, db, login_manager


def create_app(test_config=None):
    app = Flask(__name__, instance_path=str(BASE_DIR / "instance"))
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if app.config["APP_ENV"] == "production":
        secret = app.config["SECRET_KEY"]
        if (
            not os.getenv("SECRET_KEY")
            or secret == "change-this-secret-key"
            or len(secret) < 32
        ):
            raise ValueError(
                "Production requires SECRET_KEY with at least 32 characters."
            )
        app.config.update(SESSION_COOKIE_SECURE=True, REMEMBER_COOKIE_SECURE=True)
    elif app.config["SECRET_KEY"] == "change-this-secret-key":
        # An example value is never used as an actual signing key.
        import secrets

        app.config["SECRET_KEY"] = secrets.token_hex(32)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "info"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    from .routes import admin, auth, main, prediction

    for blueprint in (main.bp, auth.bp, prediction.bp, admin.bp):
        app.register_blueprint(blueprint)
    from .cli import register_commands

    register_commands(app)

    @app.context_processor
    def template_helpers():
        from datetime import datetime, timezone

        return {"current_year": datetime.now(timezone.utc).year}

    @app.template_filter("percent")
    def percent(value):
        return f"{float(value) * 100:.1f}%"

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if response.mimetype == "text/html" and not response.headers.get(
            "Cache-Control"
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(CSRFError)
    def invalid_csrf(error):
        return (
            render_template(
                "errors/400.html",
                message="Your form session expired. Refresh the page and try again.",
            ),
            400,
        )

    for code in (403, 404, 500):

        def handler(error, code=code):
            if code == 500:
                db.session.rollback()
            return render_template(f"errors/{code}.html"), code

        app.register_error_handler(code, handler)
    return app
