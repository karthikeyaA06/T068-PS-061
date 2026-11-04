import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

# Locate the project root and load .env
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    """Connect to the pharmacy MySQL database."""

    required = [
        "DB_HOST",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME"
    ]

    missing = [
        key for key in required
        if os.getenv(key) is None
    ]

    if missing:
        raise RuntimeError(
            f"Missing settings in .env: {missing}"
        )

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=5
    )

    return connection