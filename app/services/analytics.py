"""Small, shared aggregations for user and admin dashboards."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from .schema import CATEGORIES


def prediction_summary(records):
    churn = sum(record.prediction == "Yes" for record in records)
    total = len(records)
    return {
        "total": total,
        "churn": churn,
        "stay": total - churn,
        "rate": churn / total if total else 0,
    }


def prediction_charts(records):
    today = datetime.now(timezone.utc).date()
    dates = [today - timedelta(days=offset) for offset in range(13, -1, -1)]
    counts = Counter(record.created_at.date() for record in records)
    contract_counts = Counter(record.customer_data["contract"] for record in records)
    internet_counts = Counter(
        record.customer_data["internet_service"] for record in records
    )
    summary = prediction_summary(records)
    return {
        "distribution": {
            "labels": ["Likely to stay", "Likely to churn"],
            "values": [summary["stay"], summary["churn"]],
        },
        "timeline": {
            "labels": [date.strftime("%d %b") for date in dates],
            "values": [counts[date] for date in dates],
        },
        "contracts": {
            "labels": CATEGORIES["contract"],
            "values": [contract_counts[label] for label in CATEGORIES["contract"]],
        },
        "internet": {
            "labels": CATEGORIES["internet_service"],
            "values": [
                internet_counts[label] for label in CATEGORIES["internet_service"]
            ],
        },
    }
