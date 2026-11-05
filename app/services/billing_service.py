
from decimal import Decimal, ROUND_HALF_UP

import mysql.connector

from app.database.connection import get_connection
from app.repositories.billing_repository import BillingRepository
from app.services.fefo_service import FEFOSelector


class BillingService:

    CENT = Decimal("0.01")
    RUPEE = Decimal("1")

    VALID_GST_RATES = {
        Decimal("5.00"),
        Decimal("12.00")
    }

    @classmethod
    def money(cls, value):
        return Decimal(str(value)).quantize(
            cls.CENT,
            rounding=ROUND_HALF_UP
        )

    @staticmethod
    def get_loyalty_discount(schedule, loyalty_member):
        if not loyalty_member:
            return Decimal("0.00")

        rates = {
            "NONE": Decimal("10.00"),
            "H": Decimal("5.00"),
            "H1": Decimal("0.00"),
            "X": Decimal("0.00")
        }

        if schedule not in rates:
            raise ValueError("Invalid drug schedule.")

        return rates[schedule]

    @classmethod
    def get_discount_rate(
        cls, schedule, loyalty_member, near_expiry
    ):
        loyalty = cls.get_loyalty_discount(
            schedule, loyalty_member
        )

        near_expiry_discount = (
            Decimal("20.00") if near_expiry
            else Decimal("0.00")
        )

        return max(loyalty, near_expiry_discount)

    @classmethod
    def calculate_line(
        cls, quantity, mrp, pack_size,
        gst_rate, discount_rate
    ):
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity <= 0
        ):
            raise ValueError("Quantity must be positive.")

        if (
            isinstance(pack_size, bool)
            or not isinstance(pack_size, int)
            or pack_size <= 0
        ):
            raise ValueError("Pack size must be positive.")

        mrp = Decimal(str(mrp))
        gst_rate = Decimal(str(gst_rate))
        discount_rate = Decimal(str(discount_rate))

        if not mrp.is_finite() or mrp <= 0:
            raise ValueError("Invalid MRP.")

        if gst_rate not in cls.VALID_GST_RATES:
            raise ValueError("GST must be 5% or 12%.")

        if not Decimal("0") <= discount_rate <= Decimal("100"):
            raise ValueError("Invalid discount rate.")

        # Provisional assumption: MRP is per pack.
        unit_mrp = mrp / Decimal(pack_size)

        gross = cls.money(
            unit_mrp * Decimal(quantity)
        )

        discount = cls.money(
            gross * discount_rate / Decimal("100")
        )

        net_inclusive = gross - discount

        # Back-calculate GST from GST-inclusive discounted price.
        gst = cls.money(
            net_inclusive * gst_rate /
            (Decimal("100") + gst_rate)
        )

        taxable = net_inclusive - gst

        return {
            "mrp_inclusive": gross,
            "discount_rate": discount_rate,
            "discount_amount": discount,
            "gst_rate": gst_rate,
            "taxable_value": taxable,
            "gst_amount": gst,
            "line_total": net_inclusive
        }

    
    @classmethod
    def calculate_totals(cls, lines):
        subtotal = sum(
            (line["mrp_inclusive"] for line in lines),
            Decimal("0.00")
        )

        discount = sum(
            (line["discount_amount"] for line in lines),
            Decimal("0.00")
        )

        gst = sum(
            (line["gst_amount"] for line in lines),
            Decimal("0.00")
        )

        before_rounding = sum(
            (line["line_total"] for line in lines),
            Decimal("0.00")
        )

        # Round the final bill to the nearest whole rupee.
        grand_total = before_rounding.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )

        # Display the rounding adjustment.
        rounding_adjustment = grand_total - before_rounding

        return {
            "subtotal": cls.money(subtotal),
            "discount_total": cls.money(discount),
            "gst_total": cls.money(gst),
            "total_before_rounding": cls.money(before_rounding),
            "rounding_adjustment": cls.money(rounding_adjustment),
            "grand_total": grand_total
        }


    def generate_bill(self, dispense_id):
        if (
            isinstance(dispense_id, bool)
            or not isinstance(dispense_id, int)
            or dispense_id <= 0
        ):
            raise ValueError("Invalid dispense ID.")

        connection = None
        cursor = None

        try:
            connection = get_connection()
            connection.start_transaction()

            cursor = connection.cursor(dictionary=True)

            dispense = BillingRepository.get_dispense_for_update(
                cursor, dispense_id
            )

            if dispense is None:
                raise ValueError("Dispense not found.")

            if BillingRepository.get_existing_bill(
                cursor, dispense_id
            ):
                raise ValueError("Bill already exists.")

            rows = BillingRepository.get_billable_lines(
                cursor, dispense_id
            )

            if not rows:
                raise ValueError("No dispense lines found.")

            calculated_lines = []

            for row in rows:
                expiry_date = FEFOSelector.get_expiry_date(
                    row["expiry_month_start"]
                )

                days_remaining = (
                    expiry_date - row["dispensed_at"].date()
                ).days

                if days_remaining < 0:
                    raise ValueError("Cannot bill expired stock.")

                near_expiry = 0 <= days_remaining <= 90

                discount_rate = self.get_discount_rate(
                    row["schedule"],
                    bool(dispense["loyalty_member"]),
                    near_expiry
                )

                line = self.calculate_line(
                    row["quantity"],
                    row["mrp"],
                    row["pack_size"],
                    row["gst_rate"],
                    discount_rate
                )

                line.update({
                    "dispense_line_id": row["dispense_line_id"],
                    "drug_id": row["drug_id"],
                    "batch_id": row["batch_id"],
                    "quantity": row["quantity"]
                })

                calculated_lines.append(line)

            totals = self.calculate_totals(calculated_lines)

            bill_id = BillingRepository.create_bill(
                cursor,
                dispense_id,
                dispense["customer_id"],
                totals
            )

            for line in calculated_lines:
                BillingRepository.create_bill_line(
                    cursor, bill_id, line
                )

            connection.commit()

            return {
                "bill_id": bill_id,
                "dispense_id": dispense_id,
                "lines": calculated_lines,
                **totals
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
