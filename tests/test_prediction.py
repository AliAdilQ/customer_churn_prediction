import pytest

from app.extensions import db
from app.models import Prediction, User
from app.services.schema import DEFAULTS
from tests.conftest import csrf_token


def submit_prediction(client, **overrides):
    data = {**DEFAULTS, "csrf_token": csrf_token(client, "/predict"), **overrides}
    return client.post("/predict", data=data)


def test_prediction_page(user_client):
    response = user_client.get("/predict")
    assert response.status_code == 200
    assert b"Personal information" in response.data
    assert b"Account information" in response.data


def test_prediction_runs_real_pipeline_and_is_saved(user_client, app):
    response = submit_prediction(user_client)
    assert response.status_code == 302
    result = user_client.get(response.headers["Location"])
    assert result.status_code == 200
    assert b"Estimated churn probability" in result.data
    assert b"saved to prediction history" in result.data
    with app.app_context():
        record = db.session.scalar(db.select(Prediction))
        assert record.prediction in ("Yes", "No")
        assert 0 <= record.probability <= 1
        assert record.customer_data["tenure"] == DEFAULTS["tenure"]
        assert record.user.email == "user@example.com"
        assert record.model_version


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenure", -1),
        ("tenure", 12.5),
        ("tenure", 121),
        ("monthly_charges", "nan"),
        ("total_charges", "inf"),
        ("monthly_charges", "bad"),
        ("total_charges", 30001),
        ("contract", "Unknown"),
        ("senior_citizen", 2),
        ("gender", "<script>"),
    ],
)
def test_invalid_inputs_rejected(user_client, app, field, value):
    assert submit_prediction(user_client, **{field: value}).status_code == 422
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Prediction.id))) == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"phone_service": "No", "multiple_lines": "Yes"},
        {"internet_service": "No", "online_security": "Yes"},
        {"internet_service": "DSL", "online_security": "No internet service"},
    ],
)
def test_inconsistent_services_rejected(user_client, overrides):
    assert submit_prediction(user_client, **overrides).status_code == 422


def test_no_internet_or_phone_is_supported(user_client):
    from app.services.schema import SERVICE_ADDONS

    overrides = {field: "No internet service" for field in SERVICE_ADDONS}
    overrides.update(
        internet_service="No", phone_service="No", multiple_lines="No phone service"
    )
    assert submit_prediction(user_client, **overrides).status_code == 302


def test_user_cannot_see_other_users_prediction(user_client, app):
    with app.app_context():
        other = db.session.scalar(
            db.select(User).where(User.email == "other@example.com")
        )
        record = Prediction(
            user_id=other.id,
            customer_data=dict(DEFAULTS),
            prediction="Yes",
            probability=0.8,
            model_version="test",
        )
        db.session.add(record)
        db.session.commit()
        record_id = record.id
    assert user_client.get(f"/predictions/{record_id}").status_code == 404
    assert f"#{record_id:04d}".encode() not in user_client.get("/history").data
    assert b"No predictions yet" in user_client.get("/dashboard").data


def test_model_unavailable_is_friendly(user_client, app, tmp_path):
    app.config["MODEL_DIR"] = tmp_path
    response = submit_prediction(user_client)
    assert response.status_code == 503
    assert b"temporarily unavailable" in response.data


def test_prediction_requires_csrf(user_client):
    assert user_client.post("/predict", data=DEFAULTS).status_code == 400
