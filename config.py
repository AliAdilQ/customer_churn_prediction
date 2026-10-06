"""Environment configuration; production must supply its own strong secret."""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///customer_churn.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 64 * 1024
    MODEL_DIR = BASE_DIR / "models"
    DATASET_PATH = BASE_DIR / "data" / "customer_churn.csv"
    WTF_CSRF_TIME_LIMIT = 3600
