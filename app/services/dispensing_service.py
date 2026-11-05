
from datetime import date, datetime, timedelta, time
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

import mysql.connector

from app.database.connection import get_connection
from app.repositories.dispensing_repository import DispensingRepository

from app.services.fefo_service import (
    BatchCandidate,
    FEFOSelector
)

from app.services.compliance_service import (
    PrescriptionComplianceService
)


class DispensingService:
    """FEFO dispensing with prescription compliance and registers."""

    @staticmethod
    def calculate_required_units(
        dose_per_day,
        days_supply,
        pack_size,
        sells_full_packs
    ):
        dose = Decimal(str(dose_per_day))

        if not dose.is_finite() or dose <= 0:
            raise ValueError("Dose per day must be a positive finite number.")

        if (
            isinstance(days_supply, bool)
            or not isinstance(days_supply, int)
            or days_supply <= 0
        ):
            raise ValueError("Days supply must be a positive integer.")

        if (
            isinstance(pack_size, bool)
            or not isinstance(pack_size, int)
            or pack_size <= 0
        ):
            raise ValueError("Pack size must be a positive integer.")

        if not isinstance(sells_full_packs, bool):
            raise ValueError("sells_full_packs must be boolean.")

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

        # Keep database timestamps aligned with the requested business date.
        now = datetime.combine(dispense_date, datetime.now().time())

        connection = None
        cursor = None

        try:
            connection = get_connection()
            connection.start_transaction()

            cursor = connection.cursor(dictionary=True)

            # 1. Retrieve and lock prescription line.

            line = (
                DispensingRepository
                .get_prescription_line_for_update(
                    cursor, prescription_line_id
                )
            )

            if line is None:
                raise ValueError("Prescription line not found.")

            DispensingRepository.lock_patient(
                cursor, line["patient_id"]
            )

            # 2. Identify whether this is a first dispense
            #    or a refill of an already completed line.

            line_status = line["line_status"]

            if line_status not in {
                "NEW",
                "PENDING",
                "PARTIALLY_FILLED",
                "DISPENSED"
            }:
                raise ValueError(
                    "Prescription line cannot be dispensed."
                )

            is_refill_start = line_status == "DISPENSED"

            if line_status in {"PENDING", "PARTIALLY_FILLED"}:
                pending_until = line["pending_until"]

                if pending_until is None or now > pending_until:
                    raise ValueError("PENDING_LINE_EXPIRED")

            # 3. Validate prescription, doctor and schedule.

            schedule = line["schedule"]

            PrescriptionComplianceService.validate_prescription(
                schedule=schedule,
                prescription_date=line["prescription_date"],
                dispense_date=dispense_date,
                doctor_registration_number=line[
                    "registration_number"
                ],
                doctor_is_active=bool(line["doctor_is_active"]),
                days_supply=int(line["days_supply"]),
                refill_count=int(line["refill_count"])
            )

            # 4. Validate refill timing, when applicable.

            refill_count = int(line["refill_count"])

            if is_refill_start:
                first_dispensed_at = (
                    DispensingRepository.get_first_dispensed_at(
                        cursor, prescription_line_id
                    )
                )

                PrescriptionComplianceService.validate_refill(
                    schedule=schedule,
                    is_refill=True,
                    refill_count=refill_count,
                    first_dispensed_at=first_dispensed_at,
                    current_datetime=now,
                    original_days_supply=int(line["days_supply"])
                )

                refill_count += 1
                previous_dispensed = 0
                pending_until = None

            else:
                previous_dispensed = int(
                    line["dispensed_quantity"]
                )

                pending_until = line["pending_until"]

            # 5. Verify customer.

            customer = DispensingRepository.get_customer(
                cursor, customer_id
            )

            if customer is None:
                raise ValueError("Customer not found.")

            # 6. Calculate required quantity.

            required_units = self.calculate_required_units(
                line["dose_per_day"],
                int(line["days_supply"]),
                int(line["pack_size"]),
                bool(line["sells_full_packs"])
            )

            remaining_quantity = (
                required_units - previous_dispensed
            )

            if remaining_quantity <= 0:
                raise ValueError(
                    "No remaining quantity to dispense."
                )

            # 7. Retrieve and lock available batches.

            rows = DispensingRepository.get_batches_for_update(
                cursor, line["drug_id"]
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
                int(line["days_supply"])
            )

            # 8. Calculate FEFO batch allocations.

            allocations = []
            quantity_left = remaining_quantity

            full_pack_only = bool(line["sells_full_packs"])
            pack_size = int(line["pack_size"])

            for batch in eligible_batches:
                if quantity_left <= 0:
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

            # 9. If no valid stock is available, create a pending line.

            if total_dispensed == 0:
                if pending_until is None:
                    pending_until = now + timedelta(days=7)

                DispensingRepository.update_prescription_line(
                    cursor,
                    prescription_line_id,
                    required_units,
                    previous_dispensed,
                    pending_quantity,
                    "PENDING",
                    pending_until,
                    refill_count
                )

                connection.commit()

                return {
                    "status": "PENDING",
                    "dispensed_quantity": 0,
                    "pending_quantity": pending_quantity,
                    "allocations": []
                }

            # 10. Check actual dispensed days against rolling limit.

            window_start = datetime.combine(
                dispense_date - timedelta(days=89),
                time.min
            )

            window_end = datetime.combine(
                dispense_date,
                time.max
            )

            prior_days_supply = (
                DispensingRepository.get_prior_days_supply(
                    cursor,
                    line["patient_id"],
                    line["drug_id"],
                    window_start,
                    window_end
                )
            )

            actual_days_dispensed = (
                Decimal(total_dispensed)
                / Decimal(str(line["dose_per_day"]))
            )

            PrescriptionComplianceService.validate_rolling_limit(
                prior_days_supply=prior_days_supply,
                requested_days_supply=actual_days_dispensed,
                schedule=schedule
            )

            # 11. Create dispense header.

            dispense_status = (
                "PARTIAL" if pending_quantity > 0
                else "COMPLETED"
            )

            dispense_id = DispensingRepository.create_dispense(
                cursor,
                customer_id,
                line["prescription_id"],
                line["patient_id"],
                now,
                dispense_status
            )

            allocation_results = []

            # 12. Deduct stock, save dispense lines and
            #     create compliance registers.

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
                    Decimal(quantity)
                    / Decimal(str(line["dose_per_day"]))
                ).quantize(
                    Decimal("0.001"),
                    rounding=ROUND_HALF_UP
                )

                dispense_line_id = (
                    DispensingRepository.create_dispense_line(
                        cursor,
                        dispense_id,
                        prescription_line_id,
                        line["drug_id"],
                        batch.batch_id,
                        quantity,
                        days_dispensed,
                        line["brand_name"],
                        now
                    )
                )

                DispensingRepository.record_inventory_movement(
                    cursor,
                    batch.batch_id,
                    quantity,
                    dispense_id
                )

                # Schedule H1 register.

                if schedule == "H1":
                    DispensingRepository.record_h1_register(
                        cursor,
                        dispense_line_id,
                        line["patient_name"],
                        line["registration_number"],
                        now,
                        quantity
                    )

                # Schedule X register, including batch number.

                if schedule == "X":
                    DispensingRepository.record_x_register(
                        cursor,
                        dispense_line_id,
                        line["patient_name"],
                        line["registration_number"],
                        batch.batch_number,
                        now,
                        quantity
                    )

                allocation_results.append({
                    "batch_id": batch.batch_id,
                    "batch_number": batch.batch_number,
                    "quantity": quantity,
                    "remaining_stock": new_stock
                })

            # 13. Update prescription line.

            if pending_quantity > 0:
                status = "PENDING"

                if pending_until is None:
                    pending_until = now + timedelta(days=7)

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
                pending_until,
                refill_count
            )

            # 14. Commit stock, dispense, movement and registers together.

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
