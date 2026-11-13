from pathlib import Path

from prepare_mysql_test_schema import build_test_schema_script


def test_generated_integration_schema_targets_only_disposable_database():
    root = Path(__file__).resolve().parents[1]
    generated = build_test_schema_script(root)

    assert "CREATE DATABASE IF NOT EXISTS pharmacy_inventory_test;" in generated
    assert "USE pharmacy_inventory_test;" in generated
    assert "USE pharmacy_inventory;" not in generated
    assert "CREATE DATABASE IF NOT EXISTS pharmacy_inventory;" not in generated


def test_generated_schema_includes_all_migrations_in_required_order():
    root = Path(__file__).resolve().parents[1]
    generated = build_test_schema_script(root)
    markers = [
        "BEGIN app/database/schema.sql",
        "BEGIN app/database/dispensing_schema.sql",
        "BEGIN app/database/billing_schema.sql",
        "BEGIN app/database/compliance_schema.sql",
        "BEGIN app/database/operational_schema.sql",
    ]
    positions = [generated.index(marker) for marker in markers]
    assert positions == sorted(positions)
