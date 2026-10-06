"""Role-protected analytics, filtered CSV exports, and POST-only record deletion."""

import csv
import io
from functools import wraps

import pandas as pd
from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import Prediction, User
from app.services.analytics import prediction_charts, prediction_summary
from app.services.ml_service import model_bundle
from app.services.schema import CATEGORIES, FEATURES

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp.get("")
@bp.get("/")
@admin_required
def dashboard():
    records = db.session.scalars(
        db.select(Prediction).order_by(Prediction.created_at.desc())
    ).all()
    stats = prediction_summary(records)
    stats["users"] = db.session.scalar(db.select(db.func.count(User.id)))
    return render_template(
        "admin/dashboard.html",
        records=records[:5],
        stats=stats,
        charts=prediction_charts(records),
    )


@bp.get("/users")
@admin_required
def users():
    search = request.args.get("q", "").strip()[:100]
    query = db.select(User)
    if search:
        query = query.where(
            or_(
                User.name.contains(search, autoescape=True),
                User.email.contains(search, autoescape=True),
            )
        )
    page = db.paginate(
        query.order_by(User.created_at.desc(), User.id.desc()),
        per_page=10,
        max_per_page=10,
        error_out=False,
    )
    return render_template("admin/users.html", page=page, search=search)


def filtered_predictions():
    search = request.args.get("q", "").strip()[:100]
    outcome = request.args.get("outcome", "")
    contract = request.args.get("contract", "")
    query = db.select(Prediction).join(User)
    if search:
        query = query.where(
            or_(
                User.name.contains(search, autoescape=True),
                User.email.contains(search, autoescape=True),
            )
        )
    if outcome in ("Yes", "No"):
        query = query.where(Prediction.prediction == outcome)
    if contract in CATEGORIES["contract"]:
        query = query.where(
            Prediction.customer_data["contract"].as_string() == contract
        )
    return (
        query.order_by(Prediction.created_at.desc(), Prediction.id.desc()),
        search,
        outcome,
        contract,
    )


@bp.get("/predictions")
@admin_required
def predictions():
    query, search, outcome, contract = filtered_predictions()
    page = db.paginate(query, per_page=10, max_per_page=10, error_out=False)
    return render_template(
        "admin/predictions.html",
        page=page,
        search=search,
        outcome=outcome,
        contract=contract,
        contracts=CATEGORIES["contract"],
    )


def safe_csv_cell(value):
    text = str(value)
    return (
        "'" + text
        if text.lstrip().startswith(("=", "+", "-", "@"))
        or text.startswith(("\t", "\r", "\n"))
        else text
    )


@bp.get("/predictions/export")
@admin_required
def export_predictions():
    query, *_ = filtered_predictions()
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "user_name",
            "user_email",
            *FEATURES,
            "prediction",
            "churn_probability",
            "model_version",
            "created_at_utc",
        ]
    )
    for record in db.session.scalars(query):
        row = [
            record.id,
            record.user.name,
            record.user.email,
            *[record.customer_data[field] for field in FEATURES],
            record.prediction,
            round(record.probability, 6),
            record.model_version,
            record.created_at.isoformat(),
        ]
        writer.writerow([safe_csv_cell(value) for value in row])
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=churn_predictions.csv"},
    )


@bp.post("/predictions/<int:prediction_id>/delete")
@admin_required
def delete_prediction(prediction_id):
    record = db.get_or_404(Prediction, prediction_id)
    db.session.delete(record)
    db.session.commit()
    flash(f"Prediction #{prediction_id} was deleted.", "success")
    return redirect(url_for("admin.predictions"))


@bp.get("/dataset")
@admin_required
def dataset():
    from flask import current_app

    frame = pd.read_csv(current_app.config["DATASET_PATH"])
    stats = {
        "records": len(frame),
        "columns": len(frame.columns),
        "rate": frame.churn.eq("Yes").mean(),
        "tenure": frame.tenure.mean(),
        "charges": frame.monthly_charges.mean(),
        "missing": int(frame.isna().sum().sum()),
    }
    charts = {
        "distribution": {
            "labels": ["Stay", "Churn"],
            "values": [
                int(frame.churn.eq("No").sum()),
                int(frame.churn.eq("Yes").sum()),
            ],
        }
    }
    for field, name in [("contract", "contracts"), ("internet_service", "internet")]:
        labels = CATEGORIES[field]
        charts[name] = {
            "labels": labels,
            "stay": [
                int(((frame[field] == label) & (frame.churn == "No")).sum())
                for label in labels
            ],
            "churn": [
                int(((frame[field] == label) & (frame.churn == "Yes")).sum())
                for label in labels
            ],
        }
    preview_fields = [
        "gender",
        "tenure",
        "internet_service",
        "contract",
        "monthly_charges",
        "churn",
    ]
    return render_template(
        "admin/dataset.html",
        stats=stats,
        charts=charts,
        fields=preview_fields,
        preview=frame[preview_fields]
        .head(8)
        .fillna("Missing")
        .to_dict(orient="records"),
    )


@bp.get("/model")
@admin_required
def model():
    _, metadata = model_bundle()
    return render_template("admin/model.html", metadata=metadata)
