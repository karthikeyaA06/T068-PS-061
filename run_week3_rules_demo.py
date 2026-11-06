
"""Safe Week 3 demonstration. Does not modify MySQL data."""

from datetime import datetime, timedelta
from decimal import Decimal

from app.services.operational_rules_service import OperationalRulesService as Rules


def show(label, action, expected_error=None):
    try:
        result = action()
    except ValueError as exc:
        if expected_error and expected_error in str(exc):
            print(f"PASS | {label}: rejected as expected")
            return
        raise
    else:
        if expected_error:
            raise AssertionError(
                f"{label}: expected {expected_error}, received {result!r}"
            )

        print(f"PASS | {label}: {result}")


def main():
    print("PS-061 WEEK 3 OPERATIONAL RULE DEMO")
    print("Database writes: NONE\n")

    # BR-04: OTC limit.
    show(
        "BR-04 two packs allowed",
        lambda: Rules.validate_otc_sale("NONE", 20, 10)
    )

    show(
        "BR-04 more than two packs rejected",
        lambda: Rules.validate_otc_sale("NONE", 21, 10),
        "PRESCRIPTION_REQUIRED"
    )

    # BR-05: substitution.
    prescribed = {
        "brand_name": "Demo Brand A",
        "molecule": "paracetamol",
        "strength": "500 mg",
        "dosage_form": "tablet",
        "group_id": 1,
        "schedule": "NONE",
        "mrp": Decimal("25.00")
    }

    candidates = [
        {
            "brand_name": "Demo Brand B",
            "molecule": "paracetamol",
            "strength": "500 mg",
            "dosage_form": "tablet",
            "group_id": 1,
            "mrp": Decimal("22.00"),
            "available_quantity": 40,
            "status": "ACTIVE"
        },
        {
            "brand_name": "Demo Brand C",
            "molecule": "paracetamol",
            "strength": "500 mg",
            "dosage_form": "tablet",
            "group_id": 1,
            "mrp": Decimal("19.00"),
            "available_quantity": 30,
            "status": "ACTIVE"
        }
    ]

    selected = Rules.choose_substitute(prescribed, candidates)

    assert selected["candidate"]["brand_name"] == "Demo Brand C"

    show(
        "BR-05 cheapest eligible substitute",
        lambda: selected["dispensed_brand"]
    )

    # BR-07: near expiry and write-off.
    show("BR-07 day 90 near expiry", lambda: Rules.is_near_expiry(90))

    expiry = datetime(2027, 1, 31).date()

    show(
        "BR-07 valid on expiry date",
        lambda: not Rules.is_expired(expiry, expiry)
    )

    show(
        "BR-07 expired the next day",
        lambda: Rules.is_expired(
            expiry,
            datetime(2027, 2, 1).date()
        )
    )

    show(
        "BR-07 write-off value",
        lambda: Rules.calculate_writeoff_value(12, Decimal("3.25"))
    )

    # BR-08: customer return.
    sale_time = datetime(2026, 11, 1, 10, 0)

    show(
        "BR-08 exactly 60 days remaining rejected",
        lambda: Rules.validate_customer_return(
            sale_time,
            sale_time + timedelta(days=7),
            True,
            True,
            "NONE",
            60,
            Decimal("100.00")
        ),
        "INSUFFICIENT_EXPIRY_REMAINING"
    )

    show(
        "BR-08 61 days remaining accepted",
        lambda: Rules.validate_customer_return(
            sale_time,
            sale_time + timedelta(days=7),
            True,
            True,
            "NONE",
            61,
            Decimal("100.00")
        )["refund_amount"]
    )

    # BR-09: reorder quantity.
    show(
        "BR-09 reorder rounded to packs",
        lambda: Rules.calculate_reorder_quantity(9, 10, 10)
    )

    show(
        "BR-09 pending supplier return prevents reorder",
        lambda: Rules.calculate_reorder_quantity(2, 10, 10, True)
    )

    # BR-10: supplier returns and recalls.
    show(
        "BR-10 eligible never-dispensed batch",
        lambda: Rules.supplier_return_allowed(89, False)
    )

    recall_time = datetime(2026, 11, 6, 12, 0)

    show(
        "BR-10 dispense before recall",
        lambda: not Rules.is_post_recall_dispense(
            recall_time - timedelta(seconds=1),
            recall_time
        )
    )

    show(
        "BR-10 dispense after recall",
        lambda: Rules.is_post_recall_dispense(
            recall_time + timedelta(seconds=1),
            recall_time
        )
    )

    print("\nWeek 3 operational helper demo completed successfully.")
    print("Note: policy-helper demonstration only; not a full MySQL workflow.")


if __name__ == "__main__":
    main()
