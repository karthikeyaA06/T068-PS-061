
from datetime import date
from decimal import Decimal, InvalidOperation

import mysql.connector

from app.database.connection import get_connection
from app.repositories.batch_repository import BatchRepository


class BatchService:
    """Business logic for receiving and validating stock batches."""

    @staticmethod
    def _validate_positive_integer(value, field_name):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field_name} must be an integer.")

        if value <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")

        return value

    @staticmethod
    def _validate_batch_number(batch_number):
        if not isinstance(batch_number, str) or not batch_number.strip():
            raise ValueError("Batch number is required.")

        return batch_number.strip()

    @staticmethod
    def _parse_expiry_month(expiry_month):
        """Convert YYYY-MM into the first day of that month."""

        if not isinstance(expiry_month, str):
            raise ValueError("Expiry month must use YYYY-MM format.")

        try:
            parsed = date.fromisoformat(expiry_month.strip() + "-01")
        except ValueError as error:
            raise ValueError(
                "Invalid expiry month. Use YYYY-MM, for example 2027-06."
            ) from error

        if parsed.strftime("%Y-%m") != expiry_month.strip():
            raise ValueError(
                "Expiry month must use YYYY-MM format."
            )

        return parsed

    @staticmethod
    def _validate_purchase_price(value):
        try:
            price = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError("Purchase price must be a valid number.")

        if not price.is_finite() or price < 0:
            raise ValueError(
                "Purchase price must be a finite, non-negative amount."
            )

        return price

    def receive_batch(
        self,
        drug_id,
        supplier_id,
        batch_number,
        expiry_month,
        quantity,
        purchase_price,
        notes=None
    ):
        # 1. Validate input fields

        drug_id = self._validate_positive_integer(
            drug_id, "Drug ID"
        )

        supplier_id = self._validate_positive_integer(
            supplier_id, "Supplier ID"
        )

        quantity = self._validate_positive_integer(
            quantity, "Received quantity"
        )

        batch_number = self._validate_batch_number(batch_number)

        expiry_month_start = self._parse_expiry_month(
            expiry_month
        )

        purchase_price = self._validate_purchase_price(
            purchase_price
        )

        if notes is not None:
            if not isinstance(notes, str):
                raise ValueError("Notes must be text.")

            notes = notes.strip() or None

        connection = None
        cursor = None

        try:
            # 2. Establish database connection

            connection = get_connection()
            connection.start_transaction()

            cursor = connection.cursor()

            # 3. Verify registered drug

            drug = BatchRepository.get_active_drug(
                cursor, drug_id
            )

            if drug is None:
                raise ValueError(
                    f"Active drug with ID {drug_id} does not exist."
                )

            # 4. Verify supplier

            supplier = BatchRepository.get_supplier(
                cursor, supplier_id
            )

            if supplier is None:
                raise ValueError(
                    f"Active supplier with ID {supplier_id} "
                    "does not exist."
                )

            # 5. Create batch record

            batch_id = BatchRepository.create_batch(
                cursor=cursor,
                drug_id=drug_id,
                supplier_id=supplier_id,
                batch_number=batch_number,
                expiry_month_start=expiry_month_start,
                quantity=quantity,
                purchase_price=purchase_price
            )

            # 6. Record stock receipt

            BatchRepository.record_stock_receipt(
                cursor=cursor,
                batch_id=batch_id,
                quantity=quantity,
                notes=notes
            )

            # 7. Commit both operations together

            connection.commit()

            return {
                "batch_id": batch_id,
                "drug_id": drug_id,
                "supplier_id": supplier_id,
                "batch_number": batch_number,
                "quantity_received": quantity,
                "expiry_month": expiry_month,
                "status": "RECEIVED"
            }

        except mysql.connector.IntegrityError as error:

            if connection and connection.is_connected():
                connection.rollback()

            if error.errno == 1062:
                raise ValueError(
                    f"Batch '{batch_number}' is already registered "
                    f"for drug ID {drug_id}."
                ) from error

            raise

        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise

        finally:
            if cursor is not None:
                cursor.close()

            if connection is not None and connection.is_connected():
                connection.close()
