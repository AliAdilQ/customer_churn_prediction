import pytest

from app.extensions import db
from app.models import User
from tests.conftest import csrf_token


def registration_data(client, **overrides):
    return {
        "csrf_token": csrf_token(client, "/register"),
        "name": "New Member",
        "email": "new@example.com",
        "password": "Member@123",
        "confirm_password": "Member@123",
        **overrides,
    }


def test_registration_hashes_password_and_cannot_grant_admin(client, app):
    data = registration_data(client, role="admin")
    response = client.post("/register", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, New" in response.data
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == "new@example.com"))
        assert user.role == "user"
        assert user.password_hash != data["password"]
        assert user.check_password(data["password"])


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "x"},
        {"email": "bad-email"},
        {"password": "short"},
        {"confirm_password": "different"},
        {"email": "USER@EXAMPLE.COM"},
    ],
)
def test_invalid_registration(client, overrides):
    response = client.post("/register", data=registration_data(client, **overrides))
    assert response.status_code == 422


def test_login_and_logout(client, login):
    assert login().headers["Location"].endswith("/dashboard")
    response = client.post(
        "/logout", data={"csrf_token": csrf_token(client, "/dashboard")}
    )
    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 302
    assert client.get("/logout").status_code == 405


def test_invalid_login(client, login):
    response = login(password="incorrect")
    assert response.status_code == 422
    assert b"email or password is incorrect" in response.data
    assert client.get("/dashboard").status_code == 302


@pytest.mark.parametrize(
    "target", ["https://evil.example", "//evil.example", "/\\evil.example"]
)
def test_login_rejects_external_redirects(client, login, target):
    from urllib.parse import urlencode

    response = login(next_url="?" + urlencode({"next": target}))
    assert response.headers["Location"].endswith("/dashboard")


def test_login_preserves_local_destination(client, login):
    assert login(next_url="?next=/predict").headers["Location"].endswith("/predict")


def test_forms_require_csrf(client):
    assert (
        client.post(
            "/login", data={"email": "user@example.com", "password": "Testing@123"}
        ).status_code
        == 400
    )
    assert client.post("/register", data={"name": "No Token"}).status_code == 400
