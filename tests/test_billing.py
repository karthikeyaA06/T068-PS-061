
from decimal import Decimal

from app.services.billing_service import BillingService


def test_none_loyalty_discount_is_10_percent():
    assert BillingService.get_discount_rate(
        "NONE", True, False
    ) == Decimal("10.00")


def test_schedule_h_loyalty_discount_is_5_percent():
    assert BillingService.get_discount_rate(
        "H", True, False
    ) == Decimal("5.00")


def test_schedule_h1_has_no_loyalty_discount():
    assert BillingService.get_discount_rate(
        "H1", True, False
    ) == Decimal("0.00")


def test_schedule_x_has_no_loyalty_discount():
    assert BillingService.get_discount_rate(
        "X", True, False
    ) == Decimal("0.00")


def test_non_loyalty_customer_gets_no_discount():
    assert BillingService.get_discount_rate(
        "NONE", False, False
    ) == Decimal("0.00")


def test_near_expiry_overrides_loyalty():
    assert BillingService.get_discount_rate(
        "NONE", True, True
    ) == Decimal("20.00")


def test_near_expiry_discount_does_not_stack():
    assert BillingService.get_discount_rate(
        "H", True, True
    ) == Decimal("20.00")


def test_inclusive_mrp_discount_and_gst():
    result = BillingService.calculate_line(
        quantity=20,
        mrp="25.00",
        pack_size=10,
        gst_rate="5.00",
        discount_rate="10.00"
    )

    assert result["mrp_inclusive"] == Decimal("50.00")
    assert result["discount_amount"] == Decimal("5.00")
    assert result["line_total"] == Decimal("45.00")
    assert result["gst_amount"] == Decimal("2.14")
    assert result["taxable_value"] == Decimal("42.86")


def test_gst_12_percent_calculation():
    result = BillingService.calculate_line(
        quantity=10,
        mrp="100.00",
        pack_size=10,
        gst_rate="12.00",
        discount_rate="0.00"
    )

    assert result["mrp_inclusive"] == Decimal("100.00")
    assert result["gst_amount"] == Decimal("10.71")
    assert result["taxable_value"] == Decimal("89.29")


def test_final_bill_rounding_half_up():
    line = {
        "mrp_inclusive": Decimal("110.00"),
        "discount_amount": Decimal("10.00"),
        "gst_amount": Decimal("4.76"),
        "line_total": Decimal("100.50")
    }

    totals = BillingService.calculate_totals([line])

    assert totals["grand_total"] == Decimal("101.00")
    assert totals["rounding_adjustment"] == Decimal("0.50")


def test_final_bill_rounding_down():
    line = {
        "mrp_inclusive": Decimal("110.00"),
        "discount_amount": Decimal("10.00"),
        "gst_amount": Decimal("4.75"),
        "line_total": Decimal("100.49")
    }

    totals = BillingService.calculate_totals([line])

    assert totals["grand_total"] == Decimal("100.00")
    assert totals["rounding_adjustment"] == Decimal("-0.49")


def test_invalid_gst_rate_is_rejected():
    try:
        BillingService.calculate_line(
            quantity=10,
            mrp="100.00",
            pack_size=10,
            gst_rate="18.00",
            discount_rate="0.00"
        )
    except ValueError:
        return

    assert False, "Invalid GST rate should be rejected."


def test_invalid_quantity_is_rejected():
    try:
        BillingService.calculate_line(
            quantity=0,
            mrp="100.00",
            pack_size=10,
            gst_rate="5.00",
            discount_rate="0.00"
        )
    except ValueError:
        return

    assert False, "Zero quantity should be rejected."
