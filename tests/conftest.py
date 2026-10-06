"""All tests use a separate temporary SQLite database, with CSRF enabled."""

import re

import pytest

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "APP_ENV": "development",
            "SECRET_KEY": "test-only-session-key",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        }
    )
    with application.app_context():
        db.create_all()
        for name, email, role in [
            ("Test User", "user@example.com", "user"),
            ("Other User", "other@example.com", "user"),
            ("Test Admin", "admin@example.com", "admin"),
        ]:
            user = User(name=name, email=email, role=role)
            user.set_password("Testing@123")
            db.session.add(user)
        db.session.commit()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_token(client, path):
    response = client.get(path)
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    assert match, f"No CSRF token at {path} (status {response.status_code})"
    return match.group(1)


@pytest.fixture
def login(client):
    def sign_in(email="user@example.com", password="Testing@123", next_url=""):
        token = csrf_token(client, "/login")
        return client.post(
            "/login" + next_url,
            data={"csrf_token": token, "email": email, "password": password},
        )

    return sign_in


@pytest.fixture
def user_client(client, login):
    assert login().status_code == 302
    return client


@pytest.fixture
def admin_client(client, login):
    assert login("admin@example.com").status_code == 302
    return client
