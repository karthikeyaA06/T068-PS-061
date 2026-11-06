"""Transactional over-the-counter sales (BR-04).

OTC sales share the dispense/bill ledger. A NULL prescription_id identifies
an OTC header and a NULL prescription_line_id identifies its lines.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_CEILING

from app.database.connection import get_connection
from app.repositories.dispensing_repository import DispensingRepository
from app.services.fefo_service import BatchCandidate, FEFOSelector
from app.services.operational_rules_service import OperationalRulesService


class OTCSalesService:
    @staticmethod
    def calculate_pack_count(quantity, pack_size):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer.")
        if isinstance(pack_size, bool) or not isinstance(pack_size, int) or pack_size <= 0:
            raise ValueError("pack_size must be a positive integer.")
        return int((Decimal(quantity) / Decimal(pack_size)).to_integral_value(rounding=ROUND_CEILING))

    @staticmethod
    def is_otc_batch_eligible(batch, business_date):
        """Non-prescription sales cannot use batches with 30 or fewer days to expiry."""
        return (
            batch.status.upper() == "ACTIVE"
            and batch.saleable_quantity > 0
            and FEFOSelector.days_until_expiry(batch, business_date) > 30
        )

    def sell(self, customer_id, drug_id, quantity, sale_at=None):
        for value, name in ((customer_id, "customer_id"), (drug_id, "drug_id"), (quantity, "quantity")):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")
        sale_at = sale_at or datetime.now()
        if not isinstance(sale_at, datetime):
            raise ValueError("sale_at must be a datetime.")

        connection = cursor = None
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)

            # Lock the customer row so concurrent same-day purchases serialize.
            cursor.execute(
                "SELECT customer_id FROM customers WHERE customer_id = %s FOR UPDATE",
                (customer_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("CUSTOMER_NOT_FOUND")

            cursor.execute(
                """SELECT drug_id, brand_name, schedule, mrp, pack_size,
                          sells_full_packs, is_active
                   FROM drugs WHERE drug_id = %s FOR UPDATE""",
                (drug_id,),
            )
            drug = cursor.fetchone()
            if not drug or not drug["is_active"]:
                raise ValueError("ACTIVE_DRUG_NOT_FOUND")
            if drug["schedule"] != "NONE":
                raise ValueError("PRESCRIPTION_REQUIRED")

            pack_size = int(drug["pack_size"])
            requested_packs = self.calculate_pack_count(quantity, pack_size)
            if drug["sells_full_packs"] and quantity % pack_size:
                raise ValueError("FULL_PACK_QUANTITY_REQUIRED")

            day_start = datetime.combine(sale_at.date(), time.min)
            next_day = day_start + timedelta(days=1)
            # Count prior base units for this exact customer, drug and business
            # date. Convert the combined units to pack-equivalents only once;
            # rounding each partial purchase separately can incorrectly reject
            # a customer who has not exceeded two complete pack-equivalents.
            cursor.execute(
                """SELECT COALESCE(SUM(dl.quantity), 0) AS prior_units
                   FROM dispenses dp
                   JOIN dispense_lines dl ON dl.dispense_id = dp.dispense_id
                   WHERE dp.customer_id = %s
                     AND dp.prescription_id IS NULL
                     AND dl.drug_id = %s
                     AND dp.dispensed_at >= %s
                     AND dp.dispensed_at < %s""",
                (customer_id, drug_id, day_start, next_day),
            )
            prior_units = int(cursor.fetchone()["prior_units"] or 0)
            OperationalRulesService.validate_otc_sale(
                schedule=drug["schedule"],
                quantity_units=quantity,
                pack_size=pack_size,
                prior_units_today=prior_units,
                has_valid_prescription=False,
            )

            batch_rows = DispensingRepository.get_batches_for_update(cursor, drug_id)
            candidates = [
                BatchCandidate(
                    batch_id=row["batch_id"],
                    batch_number=row["batch_number"],
                    expiry_month_start=row["expiry_month_start"],
                    received_at=row["received_at"],
                    available_quantity=int(row["available_quantity"]),
                    status=row["status"],
                    reserved_quantity=int(row.get("reserved_quantity", 0)),
                )
                for row in batch_rows
            ]
            # OTC has no acute prescription. The project allows batches within
            # 30 days only for acute prescriptions, so OTC excludes <=30 days.
            eligible = [
                batch for batch in FEFOSelector.select_eligible_batches(
                    candidates, sale_at.date(), 1
                )
                if self.is_otc_batch_eligible(batch, sale_at.date())
            ]

            if drug["sells_full_packs"]:
                allocatable = [
                    (batch, (batch.saleable_quantity // pack_size) * pack_size)
                    for batch in eligible
                ]
            else:
                allocatable = [(batch, batch.saleable_quantity) for batch in eligible]

            remaining = quantity
            allocations = []
            for batch, available in allocatable:
                if remaining <= 0:
                    break
                take = min(remaining, available)
                if drug["sells_full_packs"]:
                    take = (take // pack_size) * pack_size
                if take:
                    allocations.append((batch, take))
                    remaining -= take
            if remaining:
                raise ValueError("INSUFFICIENT_VALID_STOCK")

            dispense_id = DispensingRepository.create_dispense(
                cursor, customer_id, None, None, sale_at, "COMPLETED"
            )
            line_results = []
            for batch, take in allocations:
                new_stock = batch.available_quantity - take
                DispensingRepository.update_batch_stock(cursor, batch.batch_id, new_stock)
                dispense_line_id = DispensingRepository.create_dispense_line(
                    cursor=cursor,
                    dispense_id=dispense_id,
                    prescription_line_id=None,
                    drug_id=drug_id,
                    batch_id=batch.batch_id,
                    quantity=take,
                    days_supply=Decimal("0.000"),
                    prescribed_brand=drug["brand_name"],
                    dispensed_brand=drug["brand_name"],
                    dispensed_at=sale_at,
                    is_substituted=False,
                )
                DispensingRepository.record_inventory_movement(
                    cursor, batch.batch_id, take, dispense_id
                )
                line_results.append({
                    "dispense_line_id": dispense_line_id,
                    "batch_id": batch.batch_id,
                    "batch_number": batch.batch_number,
                    "quantity": take,
                    "remaining_stock": new_stock,
                })

            connection.commit()
            return {
                "status": "COMPLETED",
                "sale_type": "OTC",
                "dispense_id": dispense_id,
                "customer_id": customer_id,
                "drug_id": drug_id,
                "quantity": quantity,
                "packs_counted": requested_packs,
                "lines": line_results,
            }
        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
