"""Guarded MySQL acceptance smoke test for PS-061.

IMPORTANT:
- This script writes synthetic records and MUST only target
  `pharmacy_inventory_test`.
- It refuses to run against `pharmacy_inventory` or any other database.
- It does not delete test data; each run uses a unique suffix.

Prepare the disposable database using docs/mysql_integration_runbook.md, then run:
    $env:DB_NAME = "pharmacy_inventory_test"
    python run_mysql_acceptance_demo.py
    Remove-Item Env:DB_NAME
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import secrets
import sys

from app.database.connection import get_connection
from app.services.master_data_service import MasterDataService
from app.services.drug_service import DrugService
from app.services.batch_service import BatchService
from app.services.prescription_service import PrescriptionService
from app.services.dispensing_service import DispensingService
from app.services.billing_service import BillingService
from app.services.otc_service import OTCSalesService
from app.services.operational_workflow_service import OperationalWorkflowService
from app.services.reporting_service import ReportingService


TEST_DATABASE = "pharmacy_inventory_test"


def check_database_name() -> str:
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        row = cursor.fetchone()
        actual = row[0] if row else None
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    if actual != TEST_DATABASE:
        raise RuntimeError(
            f"Safety stop: connected database is {actual!r}. "
            f"This script only runs against {TEST_DATABASE!r}. "
            "Set DB_NAME for this terminal session before running."
        )
    return actual


def query_one(query: str, parameters=()):
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, parameters)
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def expect_rejection(label: str, action, expected_error: str):
    try:
        action()
    except ValueError as exc:
        if expected_error not in str(exc):
            raise AssertionError(
                f"{label}: expected {expected_error!r}, received {str(exc)!r}"
            ) from exc
        print(f"PASS | {label}: rejected as expected ({exc})")
        return
    raise AssertionError(f"{label}: expected {expected_error!r} rejection.")


def register_drug(prefix, molecule, schedule, mrp, min_stock=0,
                  pack_size=10, sells_full_packs=False):
    return DrugService().register_drug(
        molecule=f"{molecule}-{prefix}",
        strength="10 mg",
        dosage_form="Tablet",
        brand_name=f"{prefix}-{schedule}-BRAND",
        schedule=schedule,
        mrp=mrp,
        gst_rate="5.00",
        pack_size=pack_size,
        min_stock=min_stock,
        sells_full_packs=sells_full_packs,
        controlled_substance=(schedule in {"H1", "X"}),
    )


def receive(drug_id, supplier_id, batch_number, expiry_month, quantity=100):
    return BatchService().receive_batch(
        drug_id=drug_id,
        supplier_id=supplier_id,
        batch_number=batch_number,
        expiry_month=expiry_month,
        quantity=quantity,
        purchase_price="5.00",
        notes="Automated acceptance demo synthetic stock",
    )


def create_and_dispense(drug_id, doctor_id, patient_id, customer_id,
                        days_supply=5, no_substitution=False):
    prescription = PrescriptionService().create_prescription(
        doctor_id=doctor_id,
        patient_id=patient_id,
        prescription_date=date.today(),
        lines=[{
            "drug_id": drug_id,
            "dose_per_day": "1.0",
            "days_supply": days_supply,
            "no_substitution": no_substitution,
        }],
    )
    line_id = prescription["lines"][0]["prescription_line_id"]
    result = DispensingService().dispense_prescription_line(
        prescription_line_id=line_id,
        customer_id=customer_id,
        dispense_date=date.today(),
    )
    return line_id, result


def main() -> int:
    try:
        database = check_database_name()
    except Exception as exc:
        print(f"SAFETY CHECK FAILED: {exc}")
        return 2

    suffix = secrets.token_hex(4).upper()
    today = date.today()
    far_expiry = f"{today.year + 1}-12"
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    next_month_expiry = next_month.strftime("%Y-%m")
    previous_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

    print(f"PS-061 LIVE MYSQL ACCEPTANCE DEMO | database={database}")
    print(f"Synthetic run ID: {suffix}")
    print("This script creates persistent synthetic records in the TEST database.\n")

    master = MasterDataService()
    supplier = master.register_supplier(f"PS061-SUP-{suffix}")
    customer = master.register_customer(f"PS061-CUST-{suffix}", loyalty_member=True)
    doctor = master.register_doctor(f"PS061-REG-{suffix}", f"PS061 Doctor {suffix}")
    patient = master.register_patient(f"PS061 Patient {suffix}")
    supplier_id = supplier["supplier_id"]
    customer_id = customer["customer_id"]
    doctor_id = doctor["doctor_id"]
    patient_id = patient["patient_id"]
    print("PASS | master data registration")

    # BR-03/06: H1 dispensing, H1 register and bill persistence.
    h1 = register_drug(suffix, "H1-MOLECULE", "H1", "30.00", min_stock=5)
    receive(h1["drug_id"], supplier_id, f"H1-{suffix}", far_expiry, 100)
    h1_line_id, h1_dispense = create_and_dispense(
        h1["drug_id"], doctor_id, patient_id, customer_id, 5, True
    )
    assert h1_dispense["status"] == "DISPENSED", h1_dispense
    h1_register = query_one(
        "SELECT COUNT(*) AS n FROM h1_register_entries WHERE dispense_line_id IN "
        "(SELECT dispense_line_id FROM dispense_lines WHERE dispense_id = %s)",
        (h1_dispense["dispense_id"],),
    )
    assert int(h1_register["n"]) >= 1, "H1 register entry missing"
    h1_bill = BillingService().generate_bill(h1_dispense["dispense_id"])
    assert h1_bill["bill_id"] > 0
    print("PASS | H1 dispensing, H1 register and bill persistence")

    # BR-03: Schedule X register includes batch number.
    schedule_x = register_drug(suffix, "X-MOLECULE", "X", "40.00", min_stock=0)
    receive(schedule_x["drug_id"], supplier_id, f"X-{suffix}", far_expiry, 50)
    _, x_dispense = create_and_dispense(
        schedule_x["drug_id"], doctor_id, patient_id, customer_id, 5, True
    )
    x_register = query_one(
        "SELECT batch_number FROM x_register_entries WHERE dispense_line_id IN "
        "(SELECT dispense_line_id FROM dispense_lines WHERE dispense_id = %s) LIMIT 1",
        (x_dispense["dispense_id"],),
    )
    assert x_register and x_register["batch_number"] == f"X-{suffix}"
    print("PASS | Schedule X dispensing and batch-number register")

    # BR-02: partial fill with pending shortfall.
    partial = register_drug(suffix, "PARTIAL-MOLECULE", "H", "20.00", min_stock=0)
    receive(partial["drug_id"], supplier_id, f"PART-{suffix}", far_expiry, 2)
    _, partial_result = create_and_dispense(
        partial["drug_id"], doctor_id, patient_id, customer_id, 5, True
    )
    assert partial_result["status"] == "PENDING"
    assert partial_result["dispensed_quantity"] == 2
    assert partial_result["pending_quantity"] == 3
    print("PASS | partial fill and seven-day pending shortfall")

    # BR-05: select the same-group substitute when prescribed brand has no stock.
    original = register_drug(suffix, "SUB-MOLECULE", "H", "50.00", min_stock=0)
    substitute = DrugService().register_drug(
        molecule=f"SUB-MOLECULE-{suffix}", strength="10 mg", dosage_form="Tablet",
        brand_name=f"{suffix}-SUBSTITUTE", schedule="H", mrp="40.00",
        gst_rate="5.00", pack_size=10, min_stock=0,
        sells_full_packs=False, controlled_substance=False,
    )
    receive(substitute["drug_id"], supplier_id, f"SUB-{suffix}", far_expiry, 50)
    _, substitute_result = create_and_dispense(
        original["drug_id"], doctor_id, patient_id, customer_id, 5, False
    )
    substituted_line = query_one(
        "SELECT is_substituted, prescribed_brand, dispensed_brand FROM dispense_lines "
        "WHERE dispense_id = %s ORDER BY dispense_line_id LIMIT 1",
        (substitute_result["dispense_id"],),
    )
    assert substituted_line and bool(substituted_line["is_substituted"])
    assert substituted_line["dispensed_brand"] == f"{suffix}-SUBSTITUTE"
    print("PASS | same-group cheapest substitute recorded")

    # BR-04/06/08: OTC sale, two-pack rejection, bill and original-batch return.
    otc = register_drug(
        suffix, "OTC-MOLECULE", "NONE", "50.00", min_stock=0,
        pack_size=10, sells_full_packs=True,
    )
    receive(otc["drug_id"], supplier_id, f"OTC-{suffix}", far_expiry, 100)
    otc_service = OTCSalesService()
    sale_at = datetime.now()
    otc_sale = otc_service.sell(customer_id, otc["drug_id"], 20, sale_at=sale_at)
    expect_rejection(
        "third OTC pack blocked",
        lambda: otc_service.sell(customer_id, otc["drug_id"], 10, sale_at=sale_at + timedelta(minutes=1)),
        expected_error="PRESCRIPTION_REQUIRED",
    )
    otc_bill = BillingService().generate_bill(otc_sale["dispense_id"])
    bill_line = query_one(
        "SELECT bill_line_id FROM bill_lines WHERE bill_id = %s LIMIT 1",
        (otc_bill["bill_id"],),
    )
    assert bill_line
    return_result = OperationalWorkflowService().process_customer_return(
        bill_line_id=int(bill_line["bill_line_id"]),
        quantity=5,
        unopened=True,
        returned_at=sale_at + timedelta(days=1),
    )
    assert return_result["status"] == "RETURN_ACCEPTED"
    print("PASS | OTC cap, billing, customer return and original-batch restoration")

    # BR-10: supplier-return reservation, cancellation and completion.
    supplier_item = register_drug(suffix, "SUPRET-MOLECULE", "NONE", "20.00", min_stock=0)
    supplier_batch = receive(
        supplier_item["drug_id"], supplier_id, f"SUPRET-{suffix}", next_month_expiry, 10
    )
    ops = OperationalWorkflowService()
    pending = ops.request_supplier_return(supplier_batch["batch_id"], quantity=2)
    ops.cancel_supplier_return(pending["supplier_return_id"])
    pending_again = ops.request_supplier_return(supplier_batch["batch_id"], quantity=2)
    completed = ops.complete_supplier_return(pending_again["supplier_return_id"])
    assert completed["status"] == "COMPLETED" and completed["stock_remaining"] == 8
    print("PASS | supplier-return reservation, cancellation and completion")

    # BR-10: recall freezes batch and recall report works.
    recalled_item = register_drug(suffix, "RECALL-MOLECULE", "NONE", "20.00", min_stock=0)
    recalled_batch = receive(
        recalled_item["drug_id"], supplier_id, f"RECALL-{suffix}", far_expiry, 10
    )
    recall = ops.recall_batch(recalled_batch["batch_id"], f"Synthetic acceptance recall {suffix}")
    frozen = query_one(
        "SELECT status FROM batches WHERE batch_id = %s",
        (recalled_batch["batch_id"],),
    )
    assert frozen and frozen["status"] == "FROZEN"
    assert ops.get_recall_violations(recall["recall_id"]) == []
    print("PASS | recall freezes batch and violation report is queryable")

    # BR-07/09: seed one expired batch for write-off and one low-stock drug for reorder.
    expired_item = register_drug(suffix, "EXPIRED-MOLECULE", "NONE", "20.00", min_stock=0)
    connection = cursor = None
    try:
        connection = get_connection()
        connection.start_transaction()
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO batches
               (drug_id, supplier_id, batch_number, expiry_month_start,
                received_quantity, available_quantity, purchase_price, status)
               VALUES (%s, %s, %s, %s, 4, 4, 5.00, 'ACTIVE')""",
            (expired_item["drug_id"], supplier_id, f"EXPIRED-{suffix}", previous_month_start),
        )
        expired_batch_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO inventory_movements
               (batch_id, movement_type, quantity_delta, reference_type, reference_id, notes)
               VALUES (%s, 'RECEIPT', 4, 'BATCH', %s, 'Synthetic acceptance seed')""",
            (expired_batch_id, str(expired_batch_id)),
        )
        connection.commit()
    except Exception:
        if connection and connection.is_connected():
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    reorder_item = register_drug(suffix, "REORDER-MOLECULE", "NONE", "20.00", min_stock=20)
    report = ops.run_end_of_day(today)
    writeoff = query_one(
        "SELECT quantity, writeoff_value FROM batch_writeoffs WHERE batch_id = %s",
        (expired_batch_id,),
    )
    assert writeoff and int(writeoff["quantity"]) == 4
    reorder = query_one(
        "SELECT reorder_quantity FROM reorder_suggestions WHERE drug_id = %s AND business_date = %s",
        (reorder_item["drug_id"], today),
    )
    assert reorder and int(reorder["reorder_quantity"]) == 60
    print("PASS | end-of-day expired write-off and pack-rounded reorder suggestion")

    # BR-09: pending supplier return suppresses reorder; cancelling releases it.
    pending_item = register_drug(suffix, "PENDING-REORDER-MOLECULE", "NONE", "20.00", min_stock=20)
    # Supplier returns are normally permitted only within 90 days of expiry.
    # Use next month's expiry so this reservation test satisfies BR-10.
    pending_batch = receive(
        pending_item["drug_id"], supplier_id, f"PENDREO-{suffix}", next_month_expiry, 10
    )
    pending_return = ops.request_supplier_return(pending_batch["batch_id"], quantity=2)
    ops.run_end_of_day(today)
    suppressed = query_one(
        "SELECT reorder_id FROM reorder_suggestions WHERE drug_id = %s AND business_date = %s",
        (pending_item["drug_id"], today),
    )
    assert suppressed is None, "Reorder must be suppressed while a supplier return is pending"
    ops.cancel_supplier_return(pending_return["supplier_return_id"])
    ops.run_end_of_day(today)
    restored = query_one(
        "SELECT reorder_quantity FROM reorder_suggestions WHERE drug_id = %s AND business_date = %s",
        (pending_item["drug_id"], today),
    )
    assert restored and int(restored["reorder_quantity"]) == 50
    print("PASS | pending supplier return suppresses reorder and cancellation releases it")

    # BR-03/command layer: date-scoped H1 and X reports are callable.
    h1_rows = ReportingService().get_h1_register_report(today, today)
    x_rows = ReportingService().get_x_register_report(today, today)
    assert any(row.get("dispense_line_id") for row in h1_rows)
    assert any(row.get("dispense_line_id") for row in x_rows)
    print("PASS | H1 and X register reports")

    print("\nMYSQL ACCEPTANCE SMOKE TEST COMPLETED SUCCESSFULLY")
    print("Synthetic data remains in pharmacy_inventory_test for inspection.")
    print(f"Run ID: {suffix}")
    print("This is a focused smoke test, not a substitute for the official evaluator file.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ACCEPTANCE TEST FAILED: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
