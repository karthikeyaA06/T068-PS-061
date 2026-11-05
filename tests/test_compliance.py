
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.services.compliance_service import (
    PrescriptionComplianceService
)


def test_schedule_h_valid_prescription():
    assert PrescriptionComplianceService.validate_prescription(
        "H", date(2026, 11, 1), date(2026, 11, 5),
        "REG-001", True, 10
    )


def test_schedule_h_expired_prescription():
    with pytest.raises(ValueError, match="REJECTED_EXPIRED_RX"):
        PrescriptionComplianceService.validate_prescription(
            "H", date(2026, 9, 1), date(2026, 11, 5),
            "REG-001", True, 10
        )


def test_invalid_doctor_is_rejected():
    with pytest.raises(ValueError, match="INVALID_DOCTOR"):
        PrescriptionComplianceService.validate_prescription(
            "H", date(2026, 11, 1), date(2026, 11, 5),
            "", False, 10
        )


def test_schedule_x_seven_days_allowed():
    assert PrescriptionComplianceService.validate_prescription(
        "X", date(2026, 11, 1), date(2026, 11, 5),
        "REG-001", True, 7
    )


def test_schedule_x_eight_days_rejected():
    with pytest.raises(ValueError, match="REJECTED_LIMIT"):
        PrescriptionComplianceService.validate_prescription(
            "X", date(2026, 11, 1), date(2026, 11, 5),
            "REG-001", True, 8
        )


def test_schedule_x_refill_rejected():
    with pytest.raises(ValueError, match="SCHEDULE_X_NO_REFILLS"):
        PrescriptionComplianceService.validate_prescription(
            "X", date(2026, 11, 1), date(2026, 11, 5),
            "REG-001", True, 5, refill_count=1
        )


def test_h1_rolling_limit_30_days():
    assert PrescriptionComplianceService.validate_rolling_limit(
        Decimal("20"), Decimal("10"), "H1"
    )


def test_h1_rolling_limit_exceeded():
    with pytest.raises(ValueError, match="REJECTED_LIMIT"):
        PrescriptionComplianceService.validate_rolling_limit(
            Decimal("20"), Decimal("11"), "H1"
        )


def test_general_rolling_limit_90_days():
    assert PrescriptionComplianceService.validate_rolling_limit(
        Decimal("60"), Decimal("30"), "H"
    )


def test_general_rolling_limit_exceeded():
    with pytest.raises(ValueError, match="REJECTED_LIMIT"):
        PrescriptionComplianceService.validate_rolling_limit(
            Decimal("80"), Decimal("11"), "H"
        )


def test_refill_before_80_percent_rejected():
    first = datetime(2026, 11, 1, 10, 0)
    current = first + timedelta(days=7)

    with pytest.raises(ValueError, match="REFILL_TOO_EARLY"):
        PrescriptionComplianceService.validate_refill(
            "H", True, 0, first, current, 10
        )


def test_refill_after_80_percent_allowed():
    first = datetime(2026, 11, 1, 10, 0)
    current = first + timedelta(days=8)

    assert PrescriptionComplianceService.validate_refill(
        "H", True, 0, first, current, 10
    )


def test_h1_second_refill_rejected():
    first = datetime(2026, 11, 1, 10, 0)
    current = first + timedelta(days=25)

    with pytest.raises(
        ValueError, match="H1_REFILL_LIMIT_EXCEEDED"
    ):
        PrescriptionComplianceService.validate_refill(
            "H1", True, 1, first, current, 30
        )


def test_schedule_x_refill_rejected():
    first = datetime(2026, 11, 1, 10, 0)
    current = first + timedelta(days=10)

    with pytest.raises(ValueError, match="SCHEDULE_X_NO_REFILLS"):
        PrescriptionComplianceService.validate_refill(
            "X", True, 0, first, current, 5
        )
