from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Prediction
from app.services.analytics import prediction_charts, prediction_summary

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/dashboard")
@login_required
def dashboard():
    records = db.session.scalars(
        db.select(Prediction)
        .where(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
    ).all()
    return render_template(
        "dashboard.html",
        records=records[:5],
        stats=prediction_summary(records),
        charts=prediction_charts(records),
    )
