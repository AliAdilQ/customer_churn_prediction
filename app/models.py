"""Users and immutable model outputs, with the original customer inputs."""

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    predictions = db.relationship("Prediction", back_populates="user", lazy="dynamic")
    __table_args__ = (
        db.CheckConstraint("role IN ('user', 'admin')", name="valid_role"),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def initials(self):
        return "".join(part[0] for part in self.name.split()[:2]).upper()


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    # JSON preserves all 19 named fields together, without duplicating the schema.
    customer_data = db.Column(db.JSON, nullable=False)
    prediction = db.Column(db.String(3), nullable=False, index=True)
    probability = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(64), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    user = db.relationship("User", back_populates="predictions")
    __table_args__ = (
        db.CheckConstraint(
            "probability >= 0 AND probability <= 1", name="valid_probability"
        ),
        db.CheckConstraint("prediction IN ('Yes', 'No')", name="valid_prediction"),
    )

    @property
    def risk(self):
        return (
            "High"
            if self.probability >= 0.65
            else "Medium" if self.probability >= 0.35 else "Low"
        )

    @property
    def confidence(self):
        return self.probability if self.prediction == "Yes" else 1 - self.probability
