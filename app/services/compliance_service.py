
from datetime import date, datetime
from decimal import Decimal


class PrescriptionComplianceService:
    """Validates prescription dates, schedules, refills and limits."""

    @staticmethod
    def validate_prescription(
        schedule,
        prescription_date,
        dispense_date,
        doctor_registration_number,
        doctor_is_active,
        days_supply,
        refill_count=0
    ):
        if isinstance(prescription_date, datetime):
            prescription_date = prescription_date.date()

        if isinstance(dispense_date, datetime):
            dispense_date = dispense_date.date()

        if not isinstance(prescription_date, date):
            raise ValueError("Invalid prescription date.")

        if not isinstance(dispense_date, date):
            raise ValueError("Invalid dispensing date.")

        schedule = str(schedule).upper()

        if schedule not in {"NONE", "H", "H1", "X"}:
            raise ValueError("Invalid drug schedule.")

        if days_supply <= 0:
            raise ValueError("Days supply must be positive.")

        if dispense_date < prescription_date:
            raise ValueError("Prescription date is in the future.")

        if schedule in {"H", "H1", "X"}:
            if not doctor_registration_number or not str(
                doctor_registration_number
            ).strip():
                raise ValueError("INVALID_DOCTOR_REGISTRATION")

            if not doctor_is_active:
                raise ValueError("INVALID_DOCTOR_REGISTRATION")

        prescription_age = (
            dispense_date - prescription_date
        ).days

        if schedule in {"H", "H1"} and prescription_age > 30:
            raise ValueError("REJECTED_EXPIRED_RX")

        if schedule == "X":
            if prescription_age > 7:
                raise ValueError("REJECTED_EXPIRED_RX")

            if days_supply > 7:
                raise ValueError("REJECTED_LIMIT")

            if refill_count > 0:
                raise ValueError("SCHEDULE_X_NO_REFILLS")

        return True

    @staticmethod
    def validate_rolling_limit(
        prior_days_supply,
        requested_days_supply,
        schedule
    ):
        """Check days already dispensed in the rolling window."""

        prior = Decimal(str(prior_days_supply))
        requested = Decimal(str(requested_days_supply))

        if (
            not prior.is_finite()
            or not requested.is_finite()
            or prior < 0
            or requested <= 0
        ):
            raise ValueError("Invalid dispensing quantity.")

        schedule = str(schedule).upper()

        limit = (
            Decimal("30")
            if schedule == "H1"
            else Decimal("90")
        )

        if prior + requested > limit:
            raise ValueError("REJECTED_LIMIT")

        return True

    @staticmethod
    def validate_refill(
        schedule,
        is_refill,
        refill_count,
        first_dispensed_at,
        current_datetime,
        original_days_supply
    ):
        """Enforce schedule-specific refill rules and 80% timing."""

        if not is_refill:
            return True

        schedule = str(schedule).upper()

        if schedule == "X":
            raise ValueError("SCHEDULE_X_NO_REFILLS")

        if schedule == "H1" and refill_count >= 1:
            raise ValueError("H1_REFILL_LIMIT_EXCEEDED")

        if first_dispensed_at is None:
            raise ValueError("FIRST_DISPENSE_NOT_FOUND")

        if isinstance(first_dispensed_at, date) and not isinstance(
            first_dispensed_at, datetime
        ):
            first_dispensed_at = datetime.combine(
                first_dispensed_at,
                datetime.min.time()
            )

        if current_datetime.tzinfo != first_dispensed_at.tzinfo:
            raise ValueError("Timestamp timezone mismatch.")

        required_elapsed_seconds = (
            Decimal(str(original_days_supply))
            * Decimal("0.80")
            * Decimal("86400")
        )

        elapsed_seconds = Decimal(str(
            (current_datetime - first_dispensed_at).total_seconds()
        ))

        if elapsed_seconds < required_elapsed_seconds:
            raise ValueError("REFILL_TOO_EARLY")

        return True
