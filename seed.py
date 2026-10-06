"""Create local demo tables and accounts; reruns never overwrite existing users."""

from datetime import datetime, timedelta, timezone

import pandas as pd

from app import create_app
from app.extensions import db
from app.models import Prediction, User
from app.services.ml_service import predict_customer
from app.services.schema import validate_customer

DEMO_ACCOUNTS = [
    ("Demo Administrator", "admin@example.com", "Admin@12345", "admin"),
    ("John Smith", "john@example.com", "User@12345", "user"),
    ("Sarah Johnson", "sarah@example.com", "User@12345", "user"),
    ("Michael Brown", "michael@example.com", "User@12345", "user"),
]


def seed_database(app):
    if app.config["APP_ENV"] == "production":
        raise RuntimeError(
            "Demo seeding is disabled in production. Create accounts through flask create-admin."
        )
    with app.app_context():
        db.create_all()
        demo_users = []
        for name, email, password, role in DEMO_ACCOUNTS:
            user = db.session.scalar(db.select(User).where(User.email == email))
            if user is None:
                user = User(
                    name=name,
                    email=email,
                    role=role,
                    created_at=datetime.now(timezone.utc) - timedelta(days=30),
                )
                user.set_password(password)
                db.session.add(user)
            elif user.role != role:
                raise RuntimeError(
                    f"Existing {email} has a different role. Seeding will not grant privileges."
                )
            if role == "user":
                demo_users.append(user)
        db.session.flush()
        if not db.session.scalar(db.select(db.func.count(Prediction.id))):
            frame = pd.read_csv(app.config["DATASET_PATH"]).dropna()
            # Select actual model scores from both sides of the threshold.
            pools = {"Yes": [], "No": []}
            for _, row in frame.sample(
                n=min(160, len(frame)), random_state=19
            ).iterrows():
                data, errors = validate_customer(row.to_dict())
                if not errors:
                    result = predict_customer(data)
                    pools[result["prediction"]].append((data, result))
            samples = pools["Yes"][:12] + pools["No"][:12]
            for index, (data, result) in enumerate(samples):
                db.session.add(
                    Prediction(
                        user=demo_users[index % 3],
                        customer_data=data,
                        **result,
                        created_at=datetime.now(timezone.utc)
                        - timedelta(days=index % 14, hours=index % 8),
                    )
                )
        db.session.commit()
        print(
            f"Database ready: {db.session.query(User).count()} users, {db.session.query(Prediction).count()} predictions."
        )


if __name__ == "__main__":
    seed_database(create_app())
