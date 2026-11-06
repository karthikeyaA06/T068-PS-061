
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class BatchCandidate:
    """Represents a batch considered for FEFO dispensing."""

    batch_id: int
    batch_number: str
    expiry_month_start: date
    received_at: datetime
    available_quantity: int
    status: str
    reserved_quantity: int = 0

    @property
    def saleable_quantity(self):
        return max(0, self.available_quantity - self.reserved_quantity)


class FEFOSelector:
    """Selects eligible batches using the FEFO business rule."""

    @staticmethod
    def get_expiry_date(expiry_month_start):
        """
        Convert the first day of an expiry month into
        the actual last calendar day of that month.
        """

        if isinstance(expiry_month_start, datetime):
            expiry_month_start = expiry_month_start.date()

        if not isinstance(expiry_month_start, date):
            raise ValueError("Expiry month must be a date.")

        if expiry_month_start.day != 1:
            raise ValueError(
                "Expiry month must start on the first day."
            )

        last_day = monthrange(
            expiry_month_start.year,
            expiry_month_start.month
        )[1]

        return date(
            expiry_month_start.year,
            expiry_month_start.month,
            last_day
        )

    @classmethod
    def days_until_expiry(cls, batch, dispense_date):
        expiry_date = cls.get_expiry_date(
            batch.expiry_month_start
        )

        return (expiry_date - dispense_date).days

    @classmethod
    def is_eligible(cls, batch, dispense_date, days_supply):
        """Check whether a batch can be selected for dispensing."""

        if isinstance(days_supply, bool) or not isinstance(days_supply, int):
            raise ValueError("Days supply must be an integer.")

        if days_supply <= 0:
            raise ValueError("Days supply must be positive.")

        if not isinstance(dispense_date, date):
            raise ValueError("Dispense date must be a date.")

        if batch.status.upper() != "ACTIVE":
            return False

        if batch.saleable_quantity <= 0:
            return False

        days_remaining = cls.days_until_expiry(
            batch, dispense_date
        )

        # Chronic prescription: 30 days or more.
        if days_supply >= 30:
            return days_remaining > 30

        # Acute prescription: less than 30 days.
        return days_remaining > 7

    @staticmethod
    def is_near_expiry(batch, dispense_date):
        """Calculate the near-expiry flag for a business date."""

        days_remaining = FEFOSelector.days_until_expiry(
            batch, dispense_date
        )

        return 0 <= days_remaining <= 90

    @classmethod
    def select_eligible_batches(
        cls,
        batches,
        dispense_date,
        days_supply
    ):
        """
        Return eligible batches in FEFO order.

        Tie-breaking:
        1. Expiry month
        2. Receipt timestamp
        3. Batch number
        """

        eligible = [
            batch
            for batch in batches
            if cls.is_eligible(
                batch,
                dispense_date,
                days_supply
            )
        ]

        return sorted(
            eligible,
            key=lambda batch: (
                batch.expiry_month_start,
                batch.received_at,
                batch.batch_number
            )
        )
