"""Read-only verification of the pharmacy database schema contract."""

import sys

from app.database.connection import get_connection

REQUIRED_TABLES = {
    "substitution_groups",
    "drugs",
    "suppliers",
    "batches",
    "customers",
    "inventory_movements",
    "doctors",
    "patients",
    "prescriptions",
    "prescription_lines",
    "dispenses",
    "dispense_lines",
    "h1_register_entries",
    "x_register_entries",
    "bills",
    "bill_lines",
    "customer_returns",
    "supplier_returns",
    "batch_recalls",
    "batch_writeoffs",
    "reorder_suggestions",
}

REQUIRED_NULLABLE_COLUMNS = {
    ("dispenses", "prescription_id"),
    ("dispenses", "patient_id"),
    ("dispense_lines", "prescription_line_id"),
}

REQUIRED_COLUMNS = {
    "dispenses": {
        "dispense_id", "customer_id", "prescription_id", "patient_id",
        "dispensed_at", "status",
    },
    "dispense_lines": {
        "dispense_line_id", "dispense_id", "prescription_line_id", "drug_id",
        "batch_id", "quantity", "days_supply_dispensed", "dispensed_at",
        "is_substituted", "prescribed_brand", "dispensed_brand",
    },
    "h1_register_entries": {
        "dispense_line_id", "patient_name", "doctor_registration_number",
        "dispense_date", "quantity",
    },
    "x_register_entries": {
        "dispense_line_id", "patient_name", "doctor_registration_number",
        "batch_number", "dispense_date", "quantity",
    },
    "bills": {
        "bill_id", "dispense_id", "customer_id", "grand_total",
    },
    "bill_lines": {
        "bill_line_id", "bill_id", "dispense_line_id", "batch_id",
        "quantity", "gst_amount", "line_total",
    },
}


def main():
    connection = cursor = None
    issues = []
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT TABLE_NAME, ENGINE
               FROM information_schema.TABLES
               WHERE TABLE_SCHEMA = DATABASE()"""
        )
        table_rows = cursor.fetchall()
        existing_tables = {row["TABLE_NAME"] for row in table_rows}
        missing_tables = sorted(REQUIRED_TABLES - existing_tables)
        for table in missing_tables:
            issues.append(f"MISSING TABLE: {table}")

        cursor.execute(
            """SELECT TABLE_NAME, COLUMN_NAME, IS_NULLABLE
               FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE()"""
        )
        column_rows = cursor.fetchall()
        columns = {}
        for row in column_rows:
            columns.setdefault(row["TABLE_NAME"], {})[row["COLUMN_NAME"]] = row["IS_NULLABLE"]

        for table, required in REQUIRED_COLUMNS.items():
            missing = sorted(required - set(columns.get(table, {})))
            for column in missing:
                issues.append(f"MISSING COLUMN: {table}.{column}")

        for table, column in sorted(REQUIRED_NULLABLE_COLUMNS):
            actual = columns.get(table, {}).get(column)
            if actual != "YES":
                issues.append(f"SCHEMA ISSUE: {table}.{column} must be nullable (found {actual})")

        if issues:
            print("Operational schema verification FAILED")
            for issue in issues:
                print(issue)
            return 1

        print("Operational schema verification PASSED")
        print(f"Verified {len(REQUIRED_TABLES)} required tables.")
        print(f"Verified {sum(len(v) for v in REQUIRED_COLUMNS.values())} critical columns.")
        print(f"Verified {len(REQUIRED_NULLABLE_COLUMNS)} nullable OTC columns.")
        return 0
    except Exception as exc:
        print(f"Operational schema verification ERROR: {type(exc).__name__}: {exc}")
        return 1
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
