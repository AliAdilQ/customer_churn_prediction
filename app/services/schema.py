"""One shared schema for dataset generation, model features, and web validation."""

import math

CATEGORIES = {
    "gender": ["Female", "Male"],
    "partner": ["Yes", "No"],
    "dependents": ["Yes", "No"],
    "phone_service": ["Yes", "No"],
    "multiple_lines": ["No", "Yes", "No phone service"],
    "internet_service": ["DSL", "Fiber optic", "No"],
    **{
        field: ["No", "Yes", "No internet service"]
        for field in (
            "online_security",
            "online_backup",
            "device_protection",
            "tech_support",
            "streaming_tv",
            "streaming_movies",
        )
    },
    "contract": ["Month-to-month", "One year", "Two year"],
    "paperless_billing": ["Yes", "No"],
    "payment_method": [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ],
}
NUMERICAL = ["senior_citizen", "tenure", "monthly_charges", "total_charges"]
FEATURES = [
    "gender",
    "senior_citizen",
    "partner",
    "dependents",
    "tenure",
    "phone_service",
    "multiple_lines",
    "internet_service",
    "online_security",
    "online_backup",
    "device_protection",
    "tech_support",
    "streaming_tv",
    "streaming_movies",
    "contract",
    "paperless_billing",
    "payment_method",
    "monthly_charges",
    "total_charges",
]
SERVICE_ADDONS = [
    "online_security",
    "online_backup",
    "device_protection",
    "tech_support",
    "streaming_tv",
    "streaming_movies",
]
GROUPS = [
    (
        "Personal information",
        "A little context about the customer.",
        ["gender", "senior_citizen", "partner", "dependents"],
    ),
    (
        "Services",
        "Choose the services on their current plan.",
        ["phone_service", "multiple_lines", "internet_service", *SERVICE_ADDONS],
    ),
    (
        "Account information",
        "Add the customer's billing and contract details.",
        [
            "tenure",
            "contract",
            "paperless_billing",
            "payment_method",
            "monthly_charges",
            "total_charges",
        ],
    ),
]
LABELS = {field: field.replace("_", " ").capitalize() for field in FEATURES}
LABELS.update(
    {
        "tenure": "Tenure (months)",
        "monthly_charges": "Monthly charges ($)",
        "total_charges": "Total charges ($)",
        "streaming_tv": "Streaming TV",
    }
)
DEFAULTS = {field: values[0] for field, values in CATEGORIES.items()}
DEFAULTS.update(
    senior_citizen=0, tenure=12, monthly_charges=79.85, total_charges=958.20
)


def validate_customer(form):
    """Validate types, ranges, and service dependencies; reject NaN and infinity."""
    data, errors = {}, {}
    for field, choices in CATEGORIES.items():
        value = form.get(field, "")
        if value not in choices:
            errors[field] = "Choose one of the available options."
        else:
            data[field] = value
    bounds = {
        "senior_citizen": (0, 1),
        "tenure": (0, 120),
        "monthly_charges": (0, 250),
        "total_charges": (0, 30000),
    }
    for field, (low, high) in bounds.items():
        try:
            value = float(form.get(field, ""))
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError
            if field in ("tenure", "senior_citizen"):
                if value != int(value):
                    raise ValueError
                value = int(value)
            data[field] = value
        except (TypeError, ValueError, OverflowError):
            errors[field] = (
                f"Enter {'a whole number' if field in ('tenure', 'senior_citizen') else 'a number'} between {low} and {high}."
            )
    if "phone_service" in data and "multiple_lines" in data:
        no_phone = data["phone_service"] == "No"
        if no_phone != (data["multiple_lines"] == "No phone service"):
            errors["multiple_lines"] = (
                "Match multiple lines to the selected phone service."
            )
    if "internet_service" in data:
        for field in SERVICE_ADDONS:
            if field in data and (data["internet_service"] == "No") != (
                data[field] == "No internet service"
            ):
                errors[field] = "Match this add-on to the selected internet service."
    return data, errors
