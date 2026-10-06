"""Recreate a seeded, synthetic telecom dataset with coherent services and noisy labels."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.schema import FEATURES, SERVICE_ADDONS
from config import BASE_DIR


def generate_dataset(samples=3000, seed=42):
    if samples < 1000:
        raise ValueError("Generate at least 1,000 records for this demo.")
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(samples):
        tenure = int(rng.integers(0, 73))
        contract = rng.choice(
            ["Month-to-month", "One year", "Two year"], p=[0.55, 0.23, 0.22]
        )
        internet = rng.choice(["DSL", "Fiber optic", "No"], p=[0.36, 0.45, 0.19])
        phone = rng.choice(["Yes", "No"], p=[0.9, 0.1])
        senior = int(rng.random() < 0.16)
        partner = rng.choice(["Yes", "No"], p=[0.48, 0.52])
        dependents = (
            "Yes" if rng.random() < (0.42 if partner == "Yes" else 0.16) else "No"
        )
        payment = rng.choice(
            [
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ],
            p=[0.34, 0.18, 0.24, 0.24],
        )
        row = dict(
            gender=rng.choice(["Female", "Male"]),
            senior_citizen=senior,
            partner=partner,
            dependents=dependents,
            tenure=tenure,
            phone_service=phone,
            multiple_lines=(
                rng.choice(["Yes", "No"]) if phone == "Yes" else "No phone service"
            ),
            internet_service=internet,
            contract=contract,
            payment_method=payment,
            paperless_billing=(
                "Yes"
                if rng.random() < (0.76 if internet == "Fiber optic" else 0.45)
                else "No"
            ),
        )
        for field in SERVICE_ADDONS:
            row[field] = (
                (
                    "Yes"
                    if rng.random() < (0.55 if contract != "Month-to-month" else 0.32)
                    else "No"
                )
                if internet != "No"
                else "No internet service"
            )
        monthly = (19 if phone == "Yes" else 0) + {
            "No": 0,
            "DSL": 29,
            "Fiber optic": 49,
        }[internet]
        monthly += 5 * (row["multiple_lines"] == "Yes") + sum(
            5 * (row[field] == "Yes") for field in SERVICE_ADDONS
        )
        monthly = round(float(np.clip(monthly + rng.normal(0, 2.8), 10, 130)), 2)
        row["monthly_charges"] = monthly
        row["total_charges"] = round(
            monthly * tenure * float(rng.uniform(0.91, 1.06)), 2
        )
        # Stochastic churn is driven by plausible account/service relationships,
        # not a deterministic rule or a target leaked into the input features.
        log_odds = (
            -1.6
            + 1.85 * (contract == "Month-to-month")
            - 0.85 * (contract == "Two year")
        )
        log_odds += (
            -0.037 * tenure
            + 0.75 * (internet == "Fiber optic")
            + 0.6 * (payment == "Electronic check")
        )
        log_odds += 0.5 * (row["online_security"] == "No") + 0.45 * (
            row["tech_support"] == "No"
        )
        log_odds += 0.32 * (row["paperless_billing"] == "Yes") - 0.25 * (
            dependents == "Yes"
        )
        log_odds += 0.012 * (monthly - 70) + 0.55 * (tenure < 6) + rng.normal(0, 0.35)
        row["churn"] = "Yes" if rng.random() < 1 / (1 + np.exp(-log_odds)) else "No"
        rows.append(row)
    frame = pd.DataFrame(rows, columns=FEATURES + ["churn"])
    # A small amount of missing billing data exercises the training imputers.
    for field in ("monthly_charges", "total_charges"):
        frame.loc[
            rng.choice(samples, size=max(1, samples // 100), replace=False), field
        ] = np.nan
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output", type=Path, default=BASE_DIR / "data" / "customer_churn.csv"
    )
    args = parser.parse_args()
    frame = generate_dataset(args.samples, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    print(f"Saved {len(frame):,} synthetic records to {args.output}")
    print(f"Churn rate: {frame.churn.eq('Yes').mean():.1%}. No real customer data.")


if __name__ == "__main__":
    main()
