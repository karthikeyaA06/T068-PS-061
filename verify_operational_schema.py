"""Read-only check that Week 3 operational migrations were applied."""

import sys
from app.database.connection import get_connection

REQUIRED_TABLES = {
    "customer_returns",
    "supplier_returns",
    "batch_recalls",
    "batch_writeoffs",
    "reorder_suggestions",
    "h1_register_entries",
    "x_register_entries",
}
REQUIRED_NULLABLE_COLUMNS = {
    ("dispenses", "prescription_id"),
    ("dispenses", "patient_id"),
    ("dispense_lines", "prescription_line_id"),
}


def main():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT TABLE_NAME FROM information_schema.TABLES
               WHERE TABLE_SCHEMA = DATABASE()"""
        )
        existing_tables = {row["TABLE_NAME"] for row in cursor.fetchall()}
        missing_tables = sorted(REQUIRED_TABLES - existing_tables)

        cursor.execute(
            """SELECT TABLE_NAME, COLUMN_NAME, IS_NULLABLE
               FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE()
                 AND TABLE_NAME IN ('dispenses','dispense_lines')"""
        )
        nullable = {
            (row["TABLE_NAME"], row["COLUMN_NAME"]): row["IS_NULLABLE"]
            for row in cursor.fetchall()
        }
        wrong_nullability = sorted(
            f"{table}.{column} must be nullable"
            for table, column in REQUIRED_NULLABLE_COLUMNS
            if nullable.get((table, column)) != "YES"
        )

        if missing_tables or wrong_nullability:
            print("Operational schema verification FAILED")
            for table in missing_tables:
                print(f"MISSING TABLE: {table}")
            for issue in wrong_nullability:
                print(f"SCHEMA ISSUE: {issue}")
            return 1

        print("Operational schema verification PASSED")
        print(f"Verified {len(REQUIRED_TABLES)} required tables and 3 nullable columns.")
        return 0
    except Exception as exc:
        print(f"Operational schema verification ERROR: {exc}")
        return 1
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
