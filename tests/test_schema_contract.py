from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "app" / "database"


def read(name):
    return (DB / name).read_text(encoding="utf-8").lower()


def test_foundation_schema_creates_customers_and_inventory_ledger():
    sql = read("schema.sql")
    assert "create table if not exists customers" in sql
    assert "create table if not exists inventory_movements" in sql
    for movement in (
        "receipt", "dispense", "customer_return", "supplier_return",
        "write_off", "recall", "adjustment",
    ):
        assert f"'{movement}'" in sql


def test_dispensing_schema_has_nullable_migration_targets():
    sql = read("dispensing_schema.sql")
    assert "create table if not exists dispenses" in sql
    assert "prescription_id int not null" in sql
    assert "patient_id int not null" in sql
    assert "prescription_line_id int not null" in sql


def test_compliance_schema_creates_both_registers():
    sql = read("compliance_schema.sql")
    assert "create table if not exists h1_register_entries" in sql
    assert "create table if not exists x_register_entries" in sql
    assert "batch_number" in sql
    assert "doctor_registration_number" in sql


def test_operational_migration_has_all_five_operational_tables():
    sql = read("operational_schema.sql")
    for table in (
        "customer_returns", "supplier_returns", "batch_recalls",
        "batch_writeoffs", "reorder_suggestions",
    ):
        assert f"create table if not exists {table}" in sql


def test_operational_migration_makes_otc_foreign_key_columns_nullable():
    sql = read("operational_schema.sql")
    assert "modify prescription_id int null" in sql
    assert "modify patient_id int null" in sql
    assert "modify prescription_line_id int null" in sql


def test_billing_schema_tracks_dispense_line_batch_and_money_fields():
    sql = read("billing_schema.sql")
    assert "create table if not exists bills" in sql
    assert "create table if not exists bill_lines" in sql
    for field in (
        "dispense_line_id", "batch_id", "quantity", "line_total",
        "taxable_value", "gst_amount", "discount_amount",
    ):
        assert field in sql
