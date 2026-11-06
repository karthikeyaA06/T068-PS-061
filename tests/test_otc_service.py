from datetime import date, datetime
import pytest

from app.services.fefo_service import BatchCandidate
from app.services.otc_service import OTCSalesService


def _batch(expiry_month, available=20, reserved=0, status="ACTIVE"):
    return BatchCandidate(
        batch_id=1,
        batch_number="OTC-001",
        expiry_month_start=date.fromisoformat(expiry_month + "-01"),
        received_at=datetime(2026, 1, 1),
        available_quantity=available,
        status=status,
        reserved_quantity=reserved,
    )


def test_otc_pack_count_exact_pack():
    assert OTCSalesService.calculate_pack_count(10, 10) == 1


def test_otc_pack_count_one_unit_over():
    assert OTCSalesService.calculate_pack_count(11, 10) == 2


def test_otc_pack_count_rejects_invalid_values():
    with pytest.raises(ValueError):
        OTCSalesService.calculate_pack_count(0, 10)
    with pytest.raises(ValueError):
        OTCSalesService.calculate_pack_count(1, 0)


def test_otc_batch_with_exactly_30_days_remaining_is_not_eligible():
    batch = _batch("2026-12")
    # Last day is Dec 31; chosen business date makes remaining exactly 30 days.
    assert OTCSalesService.is_otc_batch_eligible(batch, date(2026, 12, 1)) is False


def test_otc_batch_with_31_days_remaining_is_eligible():
    batch = _batch("2026-12")
    assert OTCSalesService.is_otc_batch_eligible(batch, date(2026, 11, 30)) is True


def test_otc_batch_reserved_for_supplier_return_is_not_eligible():
    batch = _batch("2027-05", available=20, reserved=20)
    assert OTCSalesService.is_otc_batch_eligible(batch, date(2026, 11, 6)) is False
