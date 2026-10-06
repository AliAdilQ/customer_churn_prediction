"""Explicit, interactive account creation for non-demo deployments."""

import click

from .extensions import db
from .models import User


def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create missing tables without adding demo accounts."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option()
    def create_admin(name, email, password):
        """Create a hashed administrator account without embedding credentials."""
        import re

        email = email.strip().lower()
        if (
            not 2 <= len(name.strip()) <= 100
            or len(email) > 254
            or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
            or not 8 <= len(password) <= 128
        ):
            raise click.ClickException(
                "Use a valid name, email, and a password of 8–128 characters."
            )
        if db.session.scalar(db.select(User).where(User.email == email)):
            raise click.ClickException("That email already has an account.")
        user = User(name=name.strip(), email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrator created: {email}")
