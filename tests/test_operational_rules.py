from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest

from app.services.operational_rules_service import OperationalRulesService as Rules


# BR-04: OTC daily cap
def test_br04_two_packs_per_day_allowed():
    assert Rules.validate_otc_sale("NONE", 20, 10, 0, False)


def test_br04_prior_sales_count_toward_daily_cap():
    with pytest.raises(ValueError, match="PRESCRIPTION_REQUIRED"):
        Rules.validate_otc_sale("NONE", 1, 10, 20, False)


def test_br04_scheduled_drug_requires_prescription():
    with pytest.raises(ValueError, match="PRESCRIPTION_REQUIRED"):
        Rules.validate_otc_sale("H", 1, 10, 0, False)


def test_br04_valid_prescription_bypasses_otc_cap():
    assert Rules.validate_otc_sale("NONE", 35, 10, 0, True)


# BR-05: generic substitution
def _drug(brand, mrp, stock=10, group=1, molecule="para", strength="500mg", form="tablet"):
    return {
        "brand_name": brand, "mrp": mrp, "available_quantity": stock,
        "status": "ACTIVE", "group_id": group, "molecule": molecule,
        "strength": strength, "dosage_form": form,
    }


def test_br05_cheapest_eligible_substitute_selected():
    prescribed = _drug("Brand A", "25")
    result = Rules.choose_substitute(prescribed, [
        _drug("Brand B", "20"), _drug("Brand C", "18")
    ])
    assert result["dispensed_brand"] == "Brand C"
    assert result["prescribed_brand"] == "Brand A"


def test_br05_equal_mrp_is_allowed():
    result = Rules.choose_substitute(
        _drug("Brand A", "25"), [_drug("Brand B", "25")]
    )
    assert result["status"] == "SUBSTITUTE_SELECTED"


def test_br05_more_expensive_substitute_is_rejected():
    result = Rules.choose_substitute(
        _drug("Brand A", "25"), [_drug("Brand B", "25.01")]
    )
    assert result["status"] == "PENDING"


def test_br05_wrong_group_or_no_stock_is_rejected():
    result = Rules.choose_substitute(_drug("Brand A", "25"), [
        _drug("Wrong group", "10", group=2),
        _drug("Out of stock", "10", stock=0),
    ])
    assert result["status"] == "PENDING"


def test_br05_no_substitution_keeps_line_pending():
    result = Rules.choose_substitute(
        _drug("Brand A", "25"), [_drug("Brand B", "10")],
        no_substitution=True
    )
    assert result["status"] == "PENDING"
    assert result["reason"] == "NO_SUBSTITUTION"


def test_br05_schedule_x_never_substituted():
    prescribed = _drug("Brand X", "25")
    prescribed["schedule"] = "X"
    with pytest.raises(ValueError, match="SCHEDULE_X_NO_SUBSTITUTION"):
        Rules.choose_substitute(prescribed, [_drug("Brand B", "10")])


# BR-07: near expiry and write-off
def test_br07_near_expiry_day_90_is_included():
    assert Rules.is_near_expiry(90) is True


def test_br07_day_91_is_not_near_expiry():
    assert Rules.is_near_expiry(91) is False


def test_br07_valid_through_expiry_date():
    assert Rules.is_expired(date(2026, 11, 30), date(2026, 11, 30)) is False


def test_br07_writeoff_starts_after_expiry_date():
    assert Rules.is_expired(date(2026, 11, 30), date(2026, 12, 1)) is True


def test_br07_writeoff_uses_purchase_price():
    assert Rules.calculate_writeoff_value(12, "4.25") == Decimal("51.00")


# BR-08: customer returns
def test_br08_day_7_2359_with_60_days_expiry_rejected():
    sale = datetime(2026, 11, 1, 12, 0)
    returned = datetime(2026, 11, 8, 11, 59)
    with pytest.raises(ValueError, match="INSUFFICIENT_EXPIRY_REMAINING"):
        Rules.validate_customer_return(
            sale, returned, True, True, "NONE", 60, "45.00"
        )


def test_br08_day_7_with_more_than_60_days_refunds_original_price():
    sale = datetime(2026, 11, 1, 12, 0)
    returned = sale + timedelta(days=7)
    result = Rules.validate_customer_return(
        sale, returned, True, True, "H", 61, "42.37"
    )
    assert result["refund_amount"] == Decimal("42.37")


def test_br08_h1_and_x_are_non_returnable():
    sale = datetime(2026, 11, 1, 12, 0)
    for schedule in ("H1", "X"):
        with pytest.raises(ValueError, match="SCHEDULE_NON_RETURNABLE"):
            Rules.validate_customer_return(
                sale, sale + timedelta(days=1), True, True,
                schedule, 90, "10.00"
            )


def test_br08_opened_strip_and_missing_bill_are_rejected():
    sale = datetime(2026, 11, 1, 12, 0)
    with pytest.raises(ValueError, match="ORIGINAL_BILL_REQUIRED"):
        Rules.validate_customer_return(
            sale, sale + timedelta(days=1), False, True,
            "NONE", 90, "10.00"
        )
    with pytest.raises(ValueError, match="OPENED_STRIPS_NOT_RETURNABLE"):
        Rules.validate_customer_return(
            sale, sale + timedelta(days=1), True, False,
            "NONE", 90, "10.00"
        )


# BR-09: reorder
def test_br09_reorder_quantity_rounds_up_to_whole_pack():
    # 3*20 - 19 = 41; pack size 10 => 50.
    assert Rules.calculate_reorder_quantity(19, 20, 10) == 50


def test_br09_no_reorder_when_stock_at_minimum_or_higher():
    assert Rules.calculate_reorder_quantity(20, 20, 10) == 0
    assert Rules.calculate_reorder_quantity(30, 20, 10) == 0


def test_br09_pending_supplier_return_excludes_reorder():
    assert Rules.calculate_reorder_quantity(2, 20, 10, True) == 0


# BR-10: supplier returns and timestamped recalls
def test_br10_never_dispensed_batch_with_89_days_can_be_returned():
    assert Rules.supplier_return_allowed(89, False) is True


def test_br10_exactly_90_days_or_previously_dispensed_not_returnable():
    assert Rules.supplier_return_allowed(90, False) is False
    assert Rules.supplier_return_allowed(20, True) is False


def test_br10_recalled_batch_is_return_eligible():
    assert Rules.supplier_return_allowed(150, True, recalled=True) is True


def test_br10_preserve_pre_recall_dispense_and_flag_post_recall():
    recall = datetime(2026, 11, 6, 10, 0, 0)
    before = datetime(2026, 11, 6, 9, 59, 59)
    after = datetime(2026, 11, 6, 10, 0, 1)
    assert Rules.is_post_recall_dispense(before, recall) is False
    assert Rules.is_post_recall_dispense(after, recall) is True


def test_br10_same_timestamp_is_not_after_recall_timestamp():
    stamp = datetime(2026, 11, 6, 10, 0, 0)
    assert Rules.is_post_recall_dispense(stamp, stamp) is False


# Additional daily OTC pack-boundary checks.
def test_br04_exactly_two_daily_packs_allowed():
    assert Rules.validate_otc_pack_limit(1, 1) is True


def test_br04_third_daily_pack_rejected():
    with pytest.raises(ValueError, match="PRESCRIPTION_REQUIRED"):
        Rules.validate_otc_pack_limit(2, 1)


def test_br04_invalid_pack_count_rejected():
    with pytest.raises(ValueError):
        Rules.validate_otc_pack_limit(-1, 1)


def test_br05_candidate_with_different_schedule_is_not_selected():
    prescribed = _drug("Brand A", "25")
    candidate = _drug("Brand B", "10")
    candidate["schedule"] = "H1"
    result = Rules.choose_substitute(prescribed, [candidate])
    assert result["status"] == "PENDING"
