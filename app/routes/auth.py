"""Authentication with hashed passwords, CSRF, and safe post-login destinations."""

import re
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User

bp = Blueprint("auth", __name__)


def safe_next(value):
    if (
        not value
        or not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
    ):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return not parsed.netloc and not parsed.scheme


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    errors = {}
    values = {"name": "", "email": ""}
    if request.method == "POST":
        values = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
        }
        password = request.form.get("password", "")
        if not 2 <= len(values["name"]) <= 100:
            errors["name"] = "Use a name between 2 and 100 characters."
        if len(values["email"]) > 254 or not re.fullmatch(
            r"[^\s@]+@[^\s@]+\.[^\s@]+", values["email"]
        ):
            errors["email"] = "Enter a valid email address."
        if not 8 <= len(password) <= 128:
            errors["password"] = "Use a password between 8 and 128 characters."
        if password != request.form.get("confirm_password"):
            errors["confirm_password"] = "The passwords don't match."
        if not errors:
            user = User(name=values["name"], email=values["email"], role="user")
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors["email"] = "An account already uses this email. Sign in instead."
            else:
                login_user(user)
                flash("Your account is ready. Welcome to ChurnLens!", "success")
                return redirect(url_for("main.dashboard"))
    return render_template("register.html", errors=errors, values=values), (
        422 if errors else 200
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(
            url_for(
                "admin.dashboard" if current_user.role == "admin" else "main.dashboard"
            )
        )
    error = None
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.email == email))
        if len(password) <= 128 and user and user.check_password(password):
            login_user(user)
            destination = request.args.get("next", "")
            flash(f"Welcome back, {user.name.split()[0]}.", "success")
            return redirect(
                destination
                if safe_next(destination)
                else url_for(
                    "admin.dashboard" if user.role == "admin" else "main.dashboard"
                )
            )
        error = "The email or password is incorrect. Please try again."
    return render_template("login.html", error=error, email=email), (
        422 if error else 200
    )


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You've signed out successfully.", "info")
    return redirect(url_for("main.index"))
