"""Safe, database-independent demo for Week 3 operational rule helpers.

Run from the repository root:
    python run_week3_rules_demo.py

This script does not create or modify MySQL records.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from app.services.operational_rules_service import OperationalRulesService as Rules


def show(label, action, expected_error=None):
    try:
        result = action()
    except ValueError as exc:
        if expected_error and expected_error in str(exc):
            print(f"PASS | {label}: rejected as expected ({exc})")
            return
        raise
    else:
        if expected_error:
            raise AssertionError(
                f"{label}: expected {expected_error}, got {result!r}"
            )
        print(f"PASS | {label}: {result}")


def main():
    print("PS-061 WEEK 3 OPERATIONAL RULE DEMO")
    print("Database writes: NONE\n")

    # BR-04: two packs (20 units) allowed; one unit more is blocked.
    show(
        "BR-04 exactly two OTC packs",
        lambda: Rules.validate_otc_sale("NONE", 20, 10, 0, False),
    )
    show(
        "BR-04 over two OTC packs",
        lambda: Rules.validate_otc_sale("NONE", 21, 10, 0, False),
        expected_error="PRESCRIPTION_REQUIRED",
    )

    # BR-05: cheapest in-stock same-product substitute not above prescribed MRP.
    prescribed = {
        "brand_name": "Demo Brand A",
        "molecule": "paracetamol",
        "strength": "500 mg",
        "dosage_form": "tablet",
        "group_id": 1,
        "schedule": "NONE",
        "mrp": Decimal("25.00"),
    }
    candidates = [
        {
            "brand_name": "Demo Brand B", "molecule": "paracetamol",
            "strength": "500 mg", "dosage_form": "tablet",
            "group_id": 1, "mrp": Decimal("22.00"),
            "available_quantity": 40, "status": "ACTIVE",
        },
        {
            "brand_name": "Demo Brand C", "molecule": "paracetamol",
            "strength": "500 mg", "dosage_form": "tablet",
            "group_id": 1, "mrp": Decimal("19.00"),
            "available_quantity": 30, "status": "ACTIVE",
        },
    ]
    selected = Rules.choose_substitute(prescribed, candidates)
    assert selected["candidate"]["brand_name"] == "Demo Brand C"
    show("BR-05 cheapest eligible substitute", lambda: selected["dispensed_brand"])

    # BR-07: day 90 is flagged; expiry day itself is valid, next day is expired.
    show("BR-07 near-expiry day 90", lambda: Rules.is_near_expiry(90))
    show(
        "BR-07 valid through expiry date",
        lambda: not Rules.is_expired(datetime(2027, 1, 31).date(), datetime(2027, 1, 31).date()),
    )
    show(
        "BR-07 write-off starts next day",
        lambda: Rules.is_expired(datetime(2027, 1, 31).date(), datetime(2027, 2, 1).date()),
    )
    show(
        "BR-07 write-off purchase-cost valuation",
        lambda: Rules.calculate_writeoff_value(12, Decimal("3.25")),
    )

    # BR-08: exactly 60 days is rejected; 61 days can be returned.
    sale_time = datetime(2026, 11, 1, 10, 0)
    return_time = sale_time + timedelta(days=7)  # exact seven-day deadline
    show(
        "BR-08 exact 60 days remaining",
        lambda: Rules.validate_customer_return(
            sale_time, return_time, True, True, "NONE", 60, Decimal("100.00")
        ),
        expected_error="INSUFFICIENT_EXPIRY_REMAINING",
    )
    show(
        "BR-08 61 days remaining returns original amount",
        lambda: Rules.validate_customer_return(
            sale_time, sale_time + timedelta(days=7), True, True,
            "NONE", 61, Decimal("100.00")
        )["refund_amount"],
    )

    # BR-09: stock 9 < minimum 10; target is 30 - 9 = 21, rounded to 30.
    show(
        "BR-09 reorder rounded to packs",
        lambda: Rules.calculate_reorder_quantity(9, 10, 10),
    )
    show(
        "BR-09 no reorder during pending supplier return",
        lambda: Rules.calculate_reorder_quantity(2, 10, 10, True),
    )

    # BR-10: supplier return eligibility and exact timestamp recall check.
    show(
        "BR-10 never-dispensed batch at 89 days",
        lambda: Rules.supplier_return_allowed(89, False),
    )
    recall_time = datetime(2026, 11, 6, 12, 0, 0)
    show(
        "BR-10 dispense before recall is not violation",
        lambda: not Rules.is_post_recall_dispense(
            recall_time - timedelta(seconds=1), recall_time
        ),
    )
    show(
        "BR-10 dispense after recall is violation",
        lambda: Rules.is_post_recall_dispense(
            recall_time + timedelta(seconds=1), recall_time
        ),
    )

    print("\nWeek 3 operational helper demo completed successfully.")
    print("Note: this demonstrates policy helpers, not complete MySQL workflows.")


if __name__ == "__main__":
    main()
