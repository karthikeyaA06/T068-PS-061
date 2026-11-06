
"""Pure business-rule policies for pharmacy operations."""

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING


class OperationalRulesService:

    @staticmethod
    def validate_otc_sale(
        schedule,
        quantity_units,
        pack_size,
        prior_units_today=0,
        has_valid_prescription=False
    ):
        schedule = str(schedule).upper()

        for name, value in (
            ("quantity_units", quantity_units),
            ("pack_size", pack_size),
            ("prior_units_today", prior_units_today)
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

        if quantity_units <= 0 or pack_size <= 0:
            raise ValueError("Quantity and pack size must be positive.")

        if schedule not in {"NONE", "H", "H1", "X"}:
            raise ValueError("Invalid drug schedule.")

        if schedule != "NONE" and not has_valid_prescription:
            raise ValueError("PRESCRIPTION_REQUIRED")

        if has_valid_prescription:
            return True

        daily_limit_units = 2 * pack_size

        if prior_units_today + quantity_units > daily_limit_units:
            raise ValueError("PRESCRIPTION_REQUIRED")

        return True

    @staticmethod
    def choose_substitute(
        prescribed_drug,
        candidates,
        no_substitution=False,
        prescribed_brand_available=False
    ):
        if prescribed_brand_available:
            raise ValueError("SUBSTITUTION_NOT_REQUIRED")

        if str(prescribed_drug.get("schedule", "NONE")).upper() == "X":
            raise ValueError("SCHEDULE_X_NO_SUBSTITUTION")

        if no_substitution:
            return {
                "status": "PENDING",
                "reason": "NO_SUBSTITUTION",
                "candidate": None
            }

        required = ("molecule", "strength", "dosage_form", "mrp")

        if any(key not in prescribed_drug for key in required):
            raise ValueError("Prescribed drug is missing substitution attributes.")

        prescribed_mrp = Decimal(str(prescribed_drug["mrp"]))

        if not prescribed_mrp.is_finite() or prescribed_mrp <= 0:
            raise ValueError("Invalid prescribed MRP.")

        eligible = []

        for candidate in candidates:
            if str(candidate.get("status", "")).upper() != "ACTIVE":
                continue

            available = candidate.get("available_quantity", 0)

            if (
                isinstance(available, bool)
                or not isinstance(available, int)
                or available <= 0
            ):
                continue

            if any(
                candidate.get(key) != prescribed_drug.get(key)
                for key in ("molecule", "strength", "dosage_form")
            ):
                continue

            if (
                prescribed_drug.get("group_id") is not None
                and candidate.get("group_id") != prescribed_drug.get("group_id")
            ):
                continue

            candidate_mrp = Decimal(str(candidate.get("mrp", "NaN")))

            if not candidate_mrp.is_finite() or candidate_mrp <= 0:
                continue

            if candidate_mrp <= prescribed_mrp:
                eligible.append((
                    candidate_mrp,
                    str(candidate.get("brand_name", "")),
                    candidate
                ))

        if not eligible:
            return {
                "status": "PENDING",
                "reason": "NO_ELIGIBLE_SUBSTITUTE",
                "candidate": None
            }

        eligible.sort(key=lambda item: (item[0], item[1].casefold()))

        selected = eligible[0][2]

        return {
            "status": "SUBSTITUTE_SELECTED",
            "reason": None,
            "candidate": selected,
            "prescribed_brand": prescribed_drug.get("brand_name"),
            "dispensed_brand": selected.get("brand_name")
        }

    @staticmethod
    def is_near_expiry(days_remaining):
        if isinstance(days_remaining, bool) or not isinstance(days_remaining, int):
            raise ValueError("days_remaining must be an integer.")

        return 0 <= days_remaining <= 90

    @staticmethod
    def is_expired(expiry_date, business_date):
        if isinstance(expiry_date, datetime):
            expiry_date = expiry_date.date()

        if isinstance(business_date, datetime):
            business_date = business_date.date()

        if not isinstance(expiry_date, date) or not isinstance(business_date, date):
            raise ValueError("Expiry and business dates must be dates.")

        return business_date > expiry_date

    @staticmethod
    def calculate_writeoff_value(quantity, purchase_price_per_unit):
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity < 0
        ):
            raise ValueError("Quantity must be a non-negative integer.")

        price = Decimal(str(purchase_price_per_unit))

        if not price.is_finite() or price < 0:
            raise ValueError("Purchase price must be non-negative.")

        return (Decimal(quantity) * price).quantize(Decimal("0.01"))

    @staticmethod
    def validate_customer_return(
        sale_datetime,
        return_datetime,
        original_bill_present,
        unopened,
        schedule,
        days_to_expiry,
        original_billed_amount
    ):
        if (
            not isinstance(sale_datetime, datetime)
            or not isinstance(return_datetime, datetime)
        ):
            raise ValueError("Sale and return timestamps are required.")

        if sale_datetime.tzinfo != return_datetime.tzinfo:
            raise ValueError("Timestamp timezone mismatch.")

        elapsed = return_datetime - sale_datetime

        if elapsed < timedelta(0) or elapsed > timedelta(days=7):
            raise ValueError("RETURN_WINDOW_EXPIRED")

        if not original_bill_present:
            raise ValueError("ORIGINAL_BILL_REQUIRED")

        if not unopened:
            raise ValueError("OPENED_STRIPS_NOT_RETURNABLE")

        if str(schedule).upper() in {"H1", "X"}:
            raise ValueError("SCHEDULE_NON_RETURNABLE")

        if (
            isinstance(days_to_expiry, bool)
            or not isinstance(days_to_expiry, int)
        ):
            raise ValueError("Invalid remaining expiry days.")

        if days_to_expiry <= 60:
            raise ValueError("INSUFFICIENT_EXPIRY_REMAINING")

        refund = Decimal(str(original_billed_amount))

        if not refund.is_finite() or refund < 0:
            raise ValueError("Invalid original billed amount.")

        return {
            "eligible": True,
            "refund_amount": refund.quantize(Decimal("0.01"))
        }

    @staticmethod
    def calculate_reorder_quantity(
        valid_stock,
        minimum_stock,
        pack_size,
        supplier_return_pending=False
    ):
        values = (valid_stock, minimum_stock, pack_size)

        if any(
            isinstance(v, bool) or not isinstance(v, int) or v < 0
            for v in values
        ):
            raise ValueError(
                "Stock, minimum stock and pack size must be non-negative integers."
            )

        if pack_size == 0:
            raise ValueError("Pack size must be positive.")

        if supplier_return_pending or valid_stock >= minimum_stock:
            return 0

        base = 3 * minimum_stock - valid_stock

        packs = (
            Decimal(base) / Decimal(pack_size)
        ).to_integral_value(rounding=ROUND_CEILING)

        return int(packs) * pack_size

    @staticmethod
    def supplier_return_allowed(days_to_expiry, ever_dispensed, recalled=False):
        if isinstance(days_to_expiry, bool) or not isinstance(days_to_expiry, int):
            raise ValueError("days_to_expiry must be an integer.")

        if recalled:
            return True

        return 0 <= days_to_expiry < 90 and not bool(ever_dispensed)

    @staticmethod
    def is_post_recall_dispense(dispense_datetime, recall_datetime):
        if (
            not isinstance(dispense_datetime, datetime)
            or not isinstance(recall_datetime, datetime)
        ):
            raise ValueError("Dispense and recall timestamps are required.")

        if dispense_datetime.tzinfo != recall_datetime.tzinfo:
            raise ValueError("Timestamp timezone mismatch.")

        return dispense_datetime > recall_datetime
