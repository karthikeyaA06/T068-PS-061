
from datetime import date, datetime

from app.database.connection import get_connection
from app.repositories.batch_repository import BatchRepository
from app.services.fefo_service import (
    BatchCandidate,
    FEFOSelector
)


class InventoryService:
    """Connects FEFO selection with actual MySQL inventory."""

    def get_fefo_batches(self, drug_id, dispense_date, days_supply):
        if isinstance(drug_id, bool) or not isinstance(drug_id, int) or drug_id <= 0:
            raise ValueError("Drug ID must be a positive integer.")

        if isinstance(dispense_date, datetime):
            dispense_date = dispense_date.date()

        if not isinstance(dispense_date, date):
            raise ValueError("Dispense date must be a valid date.")

        if (
            isinstance(days_supply, bool)
            or not isinstance(days_supply, int)
            or days_supply <= 0
        ):
            raise ValueError("Days supply must be a positive integer.")

        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)

            rows = BatchRepository.get_active_batches_for_drug(
                cursor, drug_id
            )

            batches = [
                BatchCandidate(
                    batch_id=row["batch_id"],
                    batch_number=row["batch_number"],
                    expiry_month_start=row["expiry_month_start"],
                    received_at=row["received_at"],
                    available_quantity=row["available_quantity"],
                    status=row["status"]
                )
                for row in rows
            ]

            return FEFOSelector.select_eligible_batches(
                batches,
                dispense_date,
                days_supply
            )

        finally:
            if cursor is not None:
                cursor.close()

            if connection is not None and connection.is_connected():
                connection.close()
