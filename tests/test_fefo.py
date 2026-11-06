
from datetime import date, datetime

from app.services.fefo_service import (
    BatchCandidate,
    FEFOSelector
)


DISPENSE_DATE = date(2026, 11, 4)


def create_batch(
    batch_id,
    batch_number,
    expiry_month,
    received_at,
    quantity=100,
    status="ACTIVE"
):
    return BatchCandidate(
        batch_id=batch_id,
        batch_number=batch_number,
        expiry_month_start=date.fromisoformat(
            expiry_month + "-01"
        ),
        received_at=datetime.fromisoformat(received_at),
        available_quantity=quantity,
        status=status
    )


def test_expiry_month_uses_last_calendar_day():
    batch = create_batch(
        1, "B001", "2027-12",
        "2026-10-01 10:00:00"
    )

    assert FEFOSelector.get_expiry_date(
        batch.expiry_month_start
    ) == date(2027, 12, 31)


def test_earliest_expiry_selected_first():
    batches = [
        create_batch(
            1, "B001", "2027-12",
            "2026-10-01 10:00:00"
        ),
        create_batch(
            2, "B002", "2027-06",
            "2026-10-02 10:00:00"
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, DISPENSE_DATE, 10
    )

    assert result[0].batch_number == "B002"


def test_same_expiry_tie_broken_by_receipt_date():
    batches = [
        create_batch(
            1, "B001", "2027-12",
            "2026-10-03 10:00:00"
        ),
        create_batch(
            2, "B002", "2027-12",
            "2026-10-01 10:00:00"
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, DISPENSE_DATE, 10
    )

    assert result[0].batch_number == "B002"


def test_same_expiry_and_receipt_tied_by_batch_number():
    batches = [
        create_batch(
            1, "Z001", "2027-12",
            "2026-10-01 10:00:00"
        ),
        create_batch(
            2, "A001", "2027-12",
            "2026-10-01 10:00:00"
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, DISPENSE_DATE, 10
    )

    assert result[0].batch_number == "A001"


def test_chronic_batch_exactly_30_days_is_excluded():
    batches = [
        create_batch(
            1, "CH30", "2026-12",
            "2026-10-01 10:00:00"
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, date(2026, 12, 1), 30
    )

    assert result == []


def test_chronic_batch_31_days_away_is_eligible():
    batches = [
        create_batch(
            1, "CH31", "2027-01",
            "2026-10-01 10:00:00"
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, date(2026, 12, 31), 30
    )

    assert len(result) == 1


def test_acute_batch_exactly_7_days_is_excluded():
    batches = [
        create_batch(
            1, "AC07", "2026-12",
            "2026-10-01 10:00:00"
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, date(2026, 12, 24), 7
    )

    assert result == []


def test_acute_batch_8_days_away_is_eligible():
    batches = [
        create_batch(
            1, "AC08", "2027-01",
            "2026-10-01 10:00:00"
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, date(2027, 1, 23), 7
    )

    assert len(result) == 1


def test_frozen_batch_is_excluded():
    batches = [
        create_batch(
            1, "FR001", "2027-12",
            "2026-10-01 10:00:00",
            status="FROZEN"
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, DISPENSE_DATE, 10
    )

    assert result == []


def test_depleted_batch_is_excluded():
    batches = [
        create_batch(
            1, "DP001", "2027-12",
            "2026-10-01 10:00:00",
            quantity=0
        )
    ]

    result = FEFOSelector.select_eligible_batches(
        batches, DISPENSE_DATE, 10
    )

    assert result == []


def test_near_expiry_flag_within_90_days():
    batch = create_batch(
        1, "NEAR001", "2026-12",
        "2026-10-01 10:00:00"
    )

    assert FEFOSelector.is_near_expiry(
        batch, date(2026, 11, 4)
    ) is True



def test_reserved_supplier_return_stock_is_not_fefo_available():
    batch = BatchCandidate(
        batch_id=99,
        batch_number="RESERVED",
        expiry_month_start=date(2027, 5, 1),
        received_at=datetime(2026, 1, 1),
        available_quantity=20,
        status="ACTIVE",
        reserved_quantity=20,
    )
    assert batch.saleable_quantity == 0
    assert FEFOSelector.is_eligible(batch, date(2026, 11, 6), 10) is False


def test_partially_reserved_batch_remains_eligible_for_unreserved_quantity():
    batch = BatchCandidate(
        batch_id=100,
        batch_number="PARTIAL-RESERVED",
        expiry_month_start=date(2027, 5, 1),
        received_at=datetime(2026, 1, 1),
        available_quantity=20,
        status="ACTIVE",
        reserved_quantity=5,
    )
    assert batch.saleable_quantity == 15
    assert FEFOSelector.is_eligible(batch, date(2026, 11, 6), 10) is True
