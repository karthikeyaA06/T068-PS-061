"""Generate a one-file schema setup for the disposable MySQL test database.

Run from the project root:
    python prepare_mysql_test_schema.py

Then open pharmacy_inventory_test_schema.sql in MySQL Workbench and execute it.
This creates/selects `pharmacy_inventory_test`, never the normal project database.
"""

from pathlib import Path

SCHEMA_FILES = (
    "app/database/schema.sql",
    "app/database/dispensing_schema.sql",
    "app/database/billing_schema.sql",
    "app/database/compliance_schema.sql",
    "app/database/operational_schema.sql",
)

OLD_DATABASE = "pharmacy_inventory"
TEST_DATABASE = "pharmacy_inventory_test"


def build_test_schema_script(project_root: Path) -> str:
    project_root = Path(project_root)
    sections = [
        "-- GENERATED FILE: disposable PS-061 MySQL integration-test schema.\n"
        "-- This script targets pharmacy_inventory_test only.\n"
        "-- Review before execution; do not change it to the production database.\n"
    ]

    for relative_path in SCHEMA_FILES:
        source_path = project_root / relative_path
        if not source_path.is_file():
            raise FileNotFoundError(f"Required schema file not found: {source_path}")
        sql = source_path.read_text(encoding="utf-8")
        sql = sql.replace(
            f"CREATE DATABASE IF NOT EXISTS {OLD_DATABASE};",
            f"CREATE DATABASE IF NOT EXISTS {TEST_DATABASE};",
        )
        sql = sql.replace(
            f"USE {OLD_DATABASE};",
            f"USE {TEST_DATABASE};",
        )
        sections.append(f"\n\n-- ===== BEGIN {relative_path} =====\n\n{sql.rstrip()}\n\n-- ===== END {relative_path} =====")

    generated = "\n".join(sections) + "\n"
    if f"USE {OLD_DATABASE};" in generated:
        raise ValueError("A schema file still contains the normal database USE statement.")
    if f"CREATE DATABASE IF NOT EXISTS {OLD_DATABASE};" in generated:
        raise ValueError("A schema file still creates the normal project database.")
    if f"CREATE DATABASE IF NOT EXISTS {TEST_DATABASE};" not in generated:
        raise ValueError("The base schema did not provide a CREATE DATABASE statement.")
    return generated


def main() -> int:
    root = Path(__file__).resolve().parent
    output_path = root / f"{TEST_DATABASE}_schema.sql"
    generated = build_test_schema_script(root)
    output_path.write_text(generated, encoding="utf-8")
    print(f"Generated: {output_path}")
    print(f"Target database: {TEST_DATABASE}")
    print("Open this generated SQL file in MySQL Workbench and execute it.")
    print("Do not execute it against the normal pharmacy_inventory database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
