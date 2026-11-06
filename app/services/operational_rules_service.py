"""Pure business-rule policies for pharmacy operations.

These helpers are intentionally database-independent. Repository/service workflows
must call them inside their own database transaction before changing stock.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING


class OperationalRulesService:
    """Implement decision logic for BR-04, BR-05 and BR-07 through BR-10."""

    @staticmethod
    def validate_otc_sale(
        schedule,
        quantity_units,
        pack_size,
        prior_units_today=0,
        has_valid_prescription=False,
    ):
        """Enforce a two-pack per-customer, per-drug, per-day OTC limit."""
        schedule = str(schedule).upper()
        for name, value in (("quantity_units", quantity_units),
                            ("pack_size", pack_size),
                            ("prior_units_today", prior_units_today)):
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
    def validate_otc_pack_limit(prior_packs_today, requested_packs, maximum_packs=2):
        """Apply the daily OTC cap across the customer's Schedule NONE purchases."""
        values = (prior_packs_today, requested_packs, maximum_packs)
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in values):
            raise ValueError("Pack counts must be non-negative integers.")
        if requested_packs <= 0 or maximum_packs <= 0:
            raise ValueError("Requested and maximum packs must be positive.")
        if prior_packs_today + requested_packs > maximum_packs:
            raise ValueError("PRESCRIPTION_REQUIRED")
        return True

    @staticmethod
    def choose_substitute(
        prescribed_drug,
        candidates,
        no_substitution=False,
        prescribed_brand_available=False,
    ):
        """Return the cheapest eligible substitute or a PENDING decision.

        A drug identity is its molecule/strength/form tuple. If a shared
        group_id is supplied on both records, it must also match.
        Candidate mappings require brand_name, molecule, strength, dosage_form,
        mrp, available_quantity and status.
        """
        if prescribed_brand_available:
            raise ValueError("SUBSTITUTION_NOT_REQUIRED")
        if str(prescribed_drug.get("schedule", "NONE")).upper() == "X":
            raise ValueError("SCHEDULE_X_NO_SUBSTITUTION")
        if no_substitution:
            return {"status": "PENDING", "reason": "NO_SUBSTITUTION", "candidate": None}

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
            candidate_schedule = str(
                candidate.get("schedule", prescribed_drug.get("schedule", "NONE"))
            ).upper()
            if candidate_schedule != str(prescribed_drug.get("schedule", "NONE")).upper():
                continue
            if candidate_schedule == "X":
                continue
            available = candidate.get("available_quantity", 0)
            if isinstance(available, bool) or not isinstance(available, int) or available <= 0:
                continue
            if any(candidate.get(k) != prescribed_drug.get(k)
                   for k in ("molecule", "strength", "dosage_form")):
                continue
            if (prescribed_drug.get("group_id") is not None
                    and candidate.get("group_id") != prescribed_drug.get("group_id")):
                continue
            candidate_mrp = Decimal(str(candidate.get("mrp", "NaN")))
            if not candidate_mrp.is_finite() or candidate_mrp <= 0:
                continue
            if candidate_mrp <= prescribed_mrp:
                eligible.append((candidate_mrp, str(candidate.get("brand_name", "")), candidate))

        if not eligible:
            return {"status": "PENDING", "reason": "NO_ELIGIBLE_SUBSTITUTE", "candidate": None}

        eligible.sort(key=lambda item: (item[0], item[1].casefold()))
        selected = eligible[0][2]
        return {
            "status": "SUBSTITUTE_SELECTED",
            "reason": None,
            "candidate": selected,
            "prescribed_brand": prescribed_drug.get("brand_name"),
            "dispensed_brand": selected.get("brand_name"),
        }

    @staticmethod
    def is_near_expiry(days_remaining):
        """Near expiry is inclusive from day 0 through day 90."""
        if isinstance(days_remaining, bool) or not isinstance(days_remaining, int):
            raise ValueError("days_remaining must be an integer.")
        return 0 <= days_remaining <= 90

    @staticmethod
    def is_expired(expiry_date, business_date):
        """A batch is valid through expiry_date; write off from the next day."""
        if isinstance(expiry_date, datetime):
            expiry_date = expiry_date.date()
        if isinstance(business_date, datetime):
            business_date = business_date.date()
        if not isinstance(expiry_date, date) or not isinstance(business_date, date):
            raise ValueError("Expiry and business dates must be dates.")
        return business_date > expiry_date

    @staticmethod
    def calculate_writeoff_value(quantity, purchase_price_per_unit):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
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
        original_billed_amount,
    ):
        """Validate a customer return and return the exact original line refund."""
        if not isinstance(sale_datetime, datetime) or not isinstance(return_datetime, datetime):
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
        if isinstance(days_to_expiry, bool) or not isinstance(days_to_expiry, int):
            raise ValueError("Invalid remaining expiry days.")
        if days_to_expiry <= 60:
            raise ValueError("INSUFFICIENT_EXPIRY_REMAINING")
        refund = Decimal(str(original_billed_amount))
        if not refund.is_finite() or refund < 0:
            raise ValueError("Invalid original billed amount.")
        return {"eligible": True, "refund_amount": refund.quantize(Decimal("0.01"))}

    @staticmethod
    def calculate_reorder_quantity(
        valid_stock,
        minimum_stock,
        pack_size,
        supplier_return_pending=False,
    ):
        """Reorder to a target of three times minimum stock, in whole packs."""
        values = (valid_stock, minimum_stock, pack_size)
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in values):
            raise ValueError("Stock, minimum stock and pack size must be non-negative integers.")
        if pack_size == 0:
            raise ValueError("Pack size must be positive.")
        if supplier_return_pending or valid_stock >= minimum_stock:
            return 0
        base = 3 * minimum_stock - valid_stock
        packs = (Decimal(base) / Decimal(pack_size)).to_integral_value(rounding=ROUND_CEILING)
        return int(packs) * pack_size

    @staticmethod
    def supplier_return_allowed(days_to_expiry, ever_dispensed, recalled=False):
        """A recall is always return-eligible; otherwise unopened stock <90 days."""
        if isinstance(days_to_expiry, bool) or not isinstance(days_to_expiry, int):
            raise ValueError("days_to_expiry must be an integer.")
        if recalled:
            return True
        return 0 <= days_to_expiry < 90 and not bool(ever_dispensed)

    @staticmethod
    def is_post_recall_dispense(dispense_datetime, recall_datetime):
        """Flag a dispense strictly after the recorded recall timestamp."""
        if not isinstance(dispense_datetime, datetime) or not isinstance(recall_datetime, datetime):
            raise ValueError("Dispense and recall timestamps are required.")
        if dispense_datetime.tzinfo != recall_datetime.tzinfo:
            raise ValueError("Timestamp timezone mismatch.")
        return dispense_datetime > recall_datetime
