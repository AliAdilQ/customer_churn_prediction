from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Prediction
from app.services.ml_service import ModelUnavailable, predict_customer
from app.services.schema import CATEGORIES, DEFAULTS, GROUPS, LABELS, validate_customer

bp = Blueprint("prediction", __name__)


@bp.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    errors, values = {}, dict(DEFAULTS)
    status = 200
    if request.method == "POST":
        values.update(request.form.to_dict())
        data, errors = validate_customer(request.form)
        if not errors:
            try:
                output = predict_customer(data)
            except ModelUnavailable:
                current_app.logger.exception("Prediction model could not be loaded")
                flash(
                    "The prediction model is temporarily unavailable. Please try again later.",
                    "danger",
                )
                status = 503
            else:
                record = Prediction(
                    user_id=current_user.id, customer_data=data, **output
                )
                db.session.add(record)
                db.session.commit()
                return redirect(url_for("prediction.result", prediction_id=record.id))
        else:
            flash("Please check the highlighted fields below.", "danger")
            status = 422
    return (
        render_template(
            "predict.html",
            groups=GROUPS,
            labels=LABELS,
            categories=CATEGORIES,
            values=values,
            errors=errors,
        ),
        status,
    )


@bp.get("/predictions/<int:prediction_id>")
@login_required
def result(prediction_id):
    record = db.get_or_404(Prediction, prediction_id)
    if record.user_id != current_user.id and current_user.role != "admin":
        abort(404)
    return render_template("result.html", record=record, labels=LABELS)


@bp.get("/history")
@login_required
def history():
    outcome = request.args.get("outcome", "")
    query = db.select(Prediction).where(Prediction.user_id == current_user.id)
    if outcome in ("Yes", "No"):
        query = query.where(Prediction.prediction == outcome)
    page = db.paginate(
        query.order_by(Prediction.created_at.desc(), Prediction.id.desc()),
        per_page=10,
        max_per_page=10,
        error_out=False,
    )
    return render_template("history.html", page=page, outcome=outcome)
