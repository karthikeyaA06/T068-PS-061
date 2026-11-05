
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

import mysql.connector

from app.database.connection import get_connection
from app.repositories.dispensing_repository import DispensingRepository

from app.services.fefo_service import (
    BatchCandidate,
    FEFOSelector
)


class DispensingService:
    """Handles FEFO dispensing and stock deduction."""

    @staticmethod
    def calculate_required_units(
        dose_per_day,
        days_supply,
        pack_size,
        sells_full_packs
    ):
        dose = Decimal(str(dose_per_day))

        if dose <= 0 or days_supply <= 0:
            raise ValueError("Dose and days supply must be positive.")

        raw_units = dose * Decimal(days_supply)

        required = int(
            raw_units.to_integral_value(
                rounding=ROUND_CEILING
            )
        )

        if sells_full_packs:
            required = (
                (required + pack_size - 1) // pack_size
            ) * pack_size

        return required

    def dispense_prescription_line(
        self,
        prescription_line_id,
        customer_id,
        dispense_date=None
    ):
        if (
            isinstance(prescription_line_id, bool)
            or not isinstance(prescription_line_id, int)
            or prescription_line_id <= 0
        ):
            raise ValueError("Invalid prescription line ID.")

        if (
            isinstance(customer_id, bool)
            or not isinstance(customer_id, int)
            or customer_id <= 0
        ):
            raise ValueError("Invalid customer ID.")

        if dispense_date is None:
            dispense_date = date.today()

        if isinstance(dispense_date, datetime):
            dispense_date = dispense_date.date()

        if not isinstance(dispense_date, date):
            raise ValueError("Invalid dispensing date.")

        now = datetime.now()

        connection = None
        cursor = None

        try:
            connection = get_connection()
            connection.start_transaction()

            cursor = connection.cursor(dictionary=True)

            # 1. Lock and retrieve prescription line

            line = DispensingRepository.get_prescription_line_for_update(
                cursor,
                prescription_line_id
            )

            if line is None:
                raise ValueError("Prescription line not found.")

            # 2. Check prescription line status

            if line["line_status"] not in (
                "NEW",
                "PENDING",
                "PARTIALLY_FILLED"
            ):
                raise ValueError(
                    "Prescription line cannot be dispensed again."
                )

            if not line["doctor_is_active"]:
                raise ValueError("Doctor registration is not valid.")

            # 3. Check prescription date

            prescription_date = line["prescription_date"]

            if prescription_date > dispense_date:
                raise ValueError("Prescription date is in the future.")

            prescription_age = (
                dispense_date - prescription_date
            ).days

            schedule = line["schedule"]

            if schedule in ("H", "H1") and prescription_age > 30:
                raise ValueError("REJECTED_EXPIRED_RX")

            if schedule == "X":
                if prescription_age > 7:
                    raise ValueError("REJECTED_EXPIRED_RX")

                if line["days_supply"] > 7:
                    raise ValueError(
                        "Schedule X supply cannot exceed 7 days."
                    )

                if line["refill_count"] > 0:
                    raise ValueError(
                        "Schedule X prescriptions cannot be refilled."
                    )

            # 4. Check customer

            customer = DispensingRepository.get_customer(
                cursor,
                customer_id
            )

            if customer is None:
                raise ValueError("Customer not found.")

            # 5. Check pending validity

            if line["line_status"] in (
                "PENDING",
                "PARTIALLY_FILLED"
            ):
                pending_until = line["pending_until"]

                if pending_until is None or now > pending_until:
                    raise ValueError("PENDING_LINE_EXPIRED")

            # 6. Calculate required units

            required_units = self.calculate_required_units(
                line["dose_per_day"],
                line["days_supply"],
                line["pack_size"],
                line["sells_full_packs"]
            )

            previous_dispensed = line["dispensed_quantity"]

            remaining_quantity = (
                required_units - previous_dispensed
            )

            if remaining_quantity <= 0:
                raise ValueError("Nothing remains to be dispensed.")

            # 7. Retrieve and lock eligible inventory rows

            rows = DispensingRepository.get_batches_for_update(
                cursor,
                line["drug_id"]
            )

            candidates = [
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

            eligible_batches = FEFOSelector.select_eligible_batches(
                candidates,
                dispense_date,
                line["days_supply"]
            )

            # 8. Allocate stock using FEFO

            allocations = []
            quantity_left = remaining_quantity

            full_pack_only = bool(line["sells_full_packs"])
            pack_size = line["pack_size"]

            for batch in eligible_batches:

                if quantity_left == 0:
                    break

                available = batch.available_quantity

                if full_pack_only:
                    available = (
                        available // pack_size
                    ) * pack_size

                quantity = min(quantity_left, available)

                if full_pack_only:
                    quantity = (
                        quantity // pack_size
                    ) * pack_size

                if quantity <= 0:
                    continue

                allocations.append((batch, quantity))

                quantity_left -= quantity

            total_dispensed = sum(
                quantity for _, quantity in allocations
            )

            new_dispensed_total = (
                previous_dispensed + total_dispensed
            )

            pending_quantity = (
                required_units - new_dispensed_total
            )

            # 9. Handle no available stock

            if total_dispensed == 0:
                if line["line_status"] == "NEW":
                    pending_until = now + timedelta(days=7)
                else:
                    pending_until = line["pending_until"]

                DispensingRepository.update_prescription_line(
                    cursor,
                    prescription_line_id,
                    required_units,
                    previous_dispensed,
                    pending_quantity,
                    "PENDING",
                    pending_until
                )

                connection.commit()

                return {
                    "status": "PENDING",
                    "dispensed_quantity": 0,
                    "pending_quantity": pending_quantity,
                    "allocations": []
                }

            # 10. Create dispensing header

            is_partial = pending_quantity > 0

            dispense_status = (
                "PARTIAL" if is_partial else "COMPLETED"
            )

            dispense_id = DispensingRepository.create_dispense(
                cursor,
                customer_id,
                line["prescription_id"],
                line["patient_id"],
                dispense_status
            )

            # 11. Deduct stock from each batch

            allocation_results = []

            dose = Decimal(str(line["dose_per_day"]))

            for batch, quantity in allocations:

                new_stock = (
                    batch.available_quantity - quantity
                )

                DispensingRepository.update_batch_stock(
                    cursor,
                    batch.batch_id,
                    new_stock
                )

                days_dispensed = (
                    Decimal(quantity) / dose
                ).quantize(
                    Decimal("0.001"),
                    rounding=ROUND_HALF_UP
                )

                DispensingRepository.create_dispense_line(
                    cursor,
                    dispense_id,
                    prescription_line_id,
                    line["drug_id"],
                    batch.batch_id,
                    quantity,
                    days_dispensed,
                    line["brand_name"]
                )

                DispensingRepository.record_inventory_movement(
                    cursor,
                    batch.batch_id,
                    quantity,
                    dispense_id
                )

                allocation_results.append({
                    "batch_number": batch.batch_number,
                    "quantity": quantity,
                    "remaining_stock": new_stock
                })

            # 12. Update prescription line

            if is_partial:
                status = "PENDING"

                if line["line_status"] == "NEW":
                    pending_until = now + timedelta(days=7)
                else:
                    pending_until = line["pending_until"]

            else:
                status = "DISPENSED"
                pending_until = None

            DispensingRepository.update_prescription_line(
                cursor,
                prescription_line_id,
                required_units,
                new_dispensed_total,
                pending_quantity,
                status,
                pending_until
            )

            # 13. Commit all stock and dispensing changes together

            connection.commit()

            return {
                "status": status,
                "dispense_id": dispense_id,
                "dispensed_quantity": total_dispensed,
                "pending_quantity": pending_quantity,
                "allocations": allocation_results
            }

        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise

        finally:
            if cursor is not None:
                cursor.close()

            if connection is not None and connection.is_connected():
                connection.close()
