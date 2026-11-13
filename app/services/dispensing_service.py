
from datetime import date, datetime, timedelta, time
from decimal import Decimal, ROUND_HALF_UP

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
from app.services.operational_rules_service import OperationalRulesService
from app.services.quantity_service import QuantityService


class DispensingService:
    """FEFO dispensing with prescription compliance and registers."""

    @staticmethod
    def rolling_window_days(schedule):
        """Return the BR-11 history window for a prescription schedule.

        H1 is limited over a rolling 30-day period; the general H/X limit
        uses a rolling 90-day period (Schedule X has additional 7-day rules).
        """
        normalized = str(schedule).upper()
        if normalized not in {"NONE", "H", "H1", "X"}:
            raise ValueError("Invalid drug schedule.")
        return 30 if normalized == "H1" else 90

    @staticmethod
    def calculate_required_units(
        dose_per_day, days_supply, pack_size, sells_full_packs
    ):
        return QuantityService.required_units(
            dose_per_day, days_supply, pack_size, sells_full_packs
        )

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
                    status=row["status"],
                    reserved_quantity=int(row.get("reserved_quantity", 0))
                )
                for row in rows
            ]

            eligible_batches = FEFOSelector.select_eligible_batches(
                candidates,
                dispense_date,
                int(line["days_supply"])
            )

            effective_drug_id = int(line["drug_id"])
            effective_brand = line["brand_name"]
            effective_pack_size = int(line["pack_size"])
            effective_sells_full_packs = bool(line["sells_full_packs"])
            is_substituted = False

            # BR-05: substitute only when no eligible prescribed-brand batch exists.
            # Schedule X is never substituted. NO_SUBSTITUTION stays pending.
            if not eligible_batches and schedule != "X":
                substitute_rows = DispensingRepository.get_substitute_drugs(
                    cursor,
                    line["group_id"],
                    line["drug_id"],
                    schedule
                )
                substitute_candidates = []
                substitute_batches = {}

                for substitute in substitute_rows:
                    substitute_batch_rows = (
                        DispensingRepository.get_batches_for_update(
                            cursor, substitute["drug_id"]
                        )
                    )
                    substitute_candidates_for_drug = [
                        BatchCandidate(
                            batch_id=batch_row["batch_id"],
                            batch_number=batch_row["batch_number"],
                            expiry_month_start=batch_row["expiry_month_start"],
                            received_at=batch_row["received_at"],
                            available_quantity=batch_row["available_quantity"],
                            status=batch_row["status"],
                            reserved_quantity=int(batch_row.get("reserved_quantity", 0))
                        )
                        for batch_row in substitute_batch_rows
                    ]
                    substitute_eligible = FEFOSelector.select_eligible_batches(
                        substitute_candidates_for_drug,
                        dispense_date,
                        int(line["days_supply"])
                    )
                    eligible_units = sum(
                        batch.saleable_quantity for batch in substitute_eligible
                    )
                    substitute_candidates.append({
                        "brand_name": substitute["brand_name"],
                        "molecule": substitute["molecule"],
                        "strength": substitute["strength"],
                        "dosage_form": substitute["dosage_form"],
                        "group_id": substitute["group_id"],
                        "schedule": substitute["schedule"],
                        "mrp": substitute["mrp"],
                        "available_quantity": eligible_units,
                        "pack_size": substitute["pack_size"],
                        "sells_full_packs": bool(substitute["sells_full_packs"]),
                        "status": substitute["status"],
                        "drug_id": substitute["drug_id"]
                    })
                    substitute_batches[int(substitute["drug_id"])] = substitute_eligible

                prescribed_drug = {
                    "brand_name": line["brand_name"],
                    "molecule": line["molecule"],
                    "strength": line["strength"],
                    "dosage_form": line["dosage_form"],
                    "group_id": line["group_id"],
                    "schedule": schedule,
                    "mrp": line["mrp"]
                }

                if line["no_substitution"]:
                    substitute_result = {
                        "status": "PENDING",
                        "reason": "NO_SUBSTITUTION",
                        "candidate": None
                    }
                else:
                    substitute_result = OperationalRulesService.choose_substitute(
                        prescribed_drug,
                        substitute_candidates,
                        no_substitution=False,
                        prescribed_brand_available=False
                    )

                if substitute_result["status"] == "SUBSTITUTE_SELECTED":
                    selected_substitute = substitute_result["candidate"]
                    effective_drug_id = int(selected_substitute["drug_id"])
                    effective_brand = selected_substitute["brand_name"]
                    eligible_batches = substitute_batches[effective_drug_id]
                    effective_pack_size = int(selected_substitute["pack_size"])
                    effective_sells_full_packs = bool(selected_substitute["sells_full_packs"])
                    required_units = self.calculate_required_units(
                        line["dose_per_day"],
                        int(line["days_supply"]),
                        effective_pack_size,
                        effective_sells_full_packs
                    )
                    remaining_quantity = required_units - previous_dispensed
                    is_substituted = True

            # 8. Calculate FEFO batch allocations from saleable, unreserved stock.
            allocations = []
            quantity_left = remaining_quantity
            full_pack_only = effective_sells_full_packs
            pack_size = effective_pack_size

            for batch in eligible_batches:
                if quantity_left <= 0:
                    break
                available = batch.saleable_quantity
                if full_pack_only:
                    available = (available // pack_size) * pack_size
                quantity = min(quantity_left, available)
                if full_pack_only:
                    quantity = (quantity // pack_size) * pack_size
                if quantity <= 0:
                    continue
                allocations.append((batch, quantity))
                quantity_left -= quantity

            total_dispensed = sum(quantity for _, quantity in allocations)

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

            rolling_days = self.rolling_window_days(schedule)
            window_start = datetime.combine(
                dispense_date - timedelta(days=rolling_days - 1),
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
                        effective_drug_id,
                        batch.batch_id,
                        quantity,
                        days_dispensed,
                        line["brand_name"],
                        effective_brand,
                        now,
                        is_substituted
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
