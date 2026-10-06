import csv
import io

import pytest

from app.extensions import db
from app.models import Prediction, User
from app.services.schema import DEFAULTS
from tests.conftest import csrf_token


def test_homepage_and_not_found(client):
    assert client.get("/").status_code == 200
    response = client.get("/unknown-page")
    assert response.status_code == 404
    assert b"out of view" in response.data


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard",
        "/predict",
        "/history",
        "/admin",
        "/admin/users",
        "/admin/predictions",
        "/admin/dataset",
        "/admin/model",
        "/admin/predictions/export",
    ],
)
def test_protected_pages_require_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/login?next=" in response.headers["Location"]


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/users",
        "/admin/predictions",
        "/admin/dataset",
        "/admin/model",
        "/admin/predictions/export",
    ],
)
def test_normal_user_cannot_access_admin(user_client, path):
    assert user_client.get(path).status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/users",
        "/admin/predictions",
        "/admin/dataset",
        "/admin/model",
        "/dashboard",
        "/history",
    ],
)
def test_admin_pages_render(admin_client, path):
    assert admin_client.get(path).status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "css/style.css",
        "css/admin.css",
        "js/main.js",
        "js/admin.js",
        "vendor/bootstrap.min.css",
        "vendor/bootstrap.bundle.min.js",
        "vendor/chart.umd.min.js",
        "images/icons.svg",
    ],
)
def test_static_assets_load(client, path):
    response = client.get("/static/" + path)
    assert response.status_code == 200
    assert len(response.data) > 100


def make_record(app, **overrides):
    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.email == "user@example.com")
        )
        record = Prediction(
            user_id=user.id,
            customer_data=dict(DEFAULTS),
            prediction="Yes",
            probability=0.8,
            model_version="test",
            **overrides,
        )
        db.session.add(record)
        db.session.commit()
        return record.id


def test_admin_delete_requires_post_and_csrf(admin_client, app):
    record_id = make_record(app)
    url = f"/admin/predictions/{record_id}/delete"
    assert admin_client.get(url).status_code == 405
    assert admin_client.post(url).status_code == 400
    response = admin_client.post(
        url, data={"csrf_token": csrf_token(admin_client, "/admin")}
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Prediction, record_id) is None


def test_user_cannot_delete(user_client, app):
    record_id = make_record(app)
    token = csrf_token(user_client, "/dashboard")
    assert (
        user_client.post(
            f"/admin/predictions/{record_id}/delete", data={"csrf_token": token}
        ).status_code
        == 403
    )
    with app.app_context():
        assert db.session.get(Prediction, record_id)


def test_csv_filters_and_neutralizes_formulas(admin_client, app):
    make_record(app)
    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.email == "user@example.com")
        )
        user.name = "=DANGEROUS()"
        db.session.commit()
    response = admin_client.get(
        "/admin/predictions/export?outcome=Yes&contract=Month-to-month"
    )
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert len(rows) == 1 and rows[0]["user_name"].startswith("'=")
    assert rows[0]["prediction"] == "Yes"
    empty = admin_client.get("/admin/predictions/export?outcome=No")
    assert len(list(csv.DictReader(io.StringIO(empty.get_data(as_text=True))))) == 0


def test_admin_search_and_filters(admin_client, app):
    make_record(app)
    assert (
        b"Likely to churn"
        in admin_client.get("/admin/predictions?q=Test&outcome=Yes").data
    )
    assert (
        b"No matching predictions"
        in admin_client.get("/admin/predictions?q=unknown").data
    )
    assert (
        b"No matching predictions"
        in admin_client.get("/admin/predictions?contract=Two+year").data
    )
