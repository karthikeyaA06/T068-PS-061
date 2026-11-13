"""Read-only stock, inventory movement, H1 and X register reports."""

from datetime import date, datetime, time, timedelta

from app.database.connection import get_connection
from app.services.fefo_service import FEFOSelector
from app.services.operational_rules_service import OperationalRulesService


class ReportingService:
    """Provide date-scoped reports without changing inventory data."""

    @staticmethod
    def _date(value, name):
        if isinstance(value, datetime):
            value = value.date()
        if not isinstance(value, date):
            raise ValueError(f"{name} must be a YYYY-MM-DD date.")
        return value

    @staticmethod
    def _datetime(value, name):
        if not isinstance(value, datetime):
            raise ValueError(f"{name} must be an ISO-8601 datetime.")
        return value

    @staticmethod
    def format_stock_row(row, as_of_date):
        """Derive report-only expiry, reserved and saleable fields."""
        as_of_date = ReportingService._date(as_of_date, "as_of_date")
        expiry_date = FEFOSelector.get_expiry_date(row["expiry_month_start"])
        days_to_expiry = (expiry_date - as_of_date).days
        available = int(row["available_quantity"] or 0)
        reserved = int(row.get("reserved_quantity", 0) or 0)
        status = str(row["status"]).upper()
        valid = status == "ACTIVE" and not OperationalRulesService.is_expired(
            expiry_date, as_of_date
        )
        saleable = max(0, available - reserved) if valid else 0
        return {
            **row,
            "expiry_date": expiry_date,
            "days_to_expiry": days_to_expiry,
            "reserved_supplier_return_quantity": reserved,
            "saleable_quantity": saleable,
            "near_expiry": bool(valid and OperationalRulesService.is_near_expiry(days_to_expiry)),
        }

    @staticmethod
    def _run_query(query, params):
        connection = cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def get_stock_report(self, as_of_date=None):
        as_of_date = self._date(as_of_date or date.today(), "as_of_date")
        query = """
            SELECT
                d.drug_id,
                d.brand_name,
                d.schedule,
                d.min_stock,
                sg.molecule,
                sg.strength,
                sg.dosage_form,
                b.batch_id,
                b.batch_number,
                b.expiry_month_start,
                b.received_at,
                b.received_quantity,
                b.available_quantity,
                b.purchase_price,
                b.status,
                COALESCE(sr.reserved_quantity, 0) AS reserved_quantity
            FROM batches b
            JOIN drugs d ON d.drug_id = b.drug_id
            JOIN substitution_groups sg ON sg.group_id = d.group_id
            LEFT JOIN (
                SELECT batch_id, SUM(quantity) AS reserved_quantity
                FROM supplier_returns
                WHERE status = 'PENDING'
                GROUP BY batch_id
            ) sr ON sr.batch_id = b.batch_id
            ORDER BY d.drug_id, b.expiry_month_start, b.received_at, b.batch_number
        """
        rows = self._run_query(query, ())
        return [self.format_stock_row(row, as_of_date) for row in rows]

    def get_h1_register_report(self, start_date, end_date):
        start_date = self._date(start_date, "start_date")
        end_date = self._date(end_date, "end_date")
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date.")
        start_at = datetime.combine(start_date, time.min)
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min)
        return self._run_query(
            """SELECT h1_entry_id, dispense_line_id, patient_name,
                      doctor_registration_number, dispense_date, quantity
               FROM h1_register_entries
               WHERE dispense_date >= %s AND dispense_date < %s
               ORDER BY dispense_date, h1_entry_id""",
            (start_at, end_exclusive),
        )

    def get_x_register_report(self, start_date, end_date):
        start_date = self._date(start_date, "start_date")
        end_date = self._date(end_date, "end_date")
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date.")
        start_at = datetime.combine(start_date, time.min)
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min)
        return self._run_query(
            """SELECT x_entry_id, dispense_line_id, patient_name,
                      doctor_registration_number, batch_number, dispense_date, quantity
               FROM x_register_entries
               WHERE dispense_date >= %s AND dispense_date < %s
               ORDER BY dispense_date, x_entry_id""",
            (start_at, end_exclusive),
        )

    def get_inventory_movement_report(self, start_at, end_at):
        start_at = self._datetime(start_at, "start_at")
        end_at = self._datetime(end_at, "end_at")
        if end_at < start_at:
            raise ValueError("end_at must be on or after start_at.")
        return self._run_query(
            """SELECT im.movement_id, im.batch_id, b.batch_number,
                      b.drug_id, d.brand_name, im.movement_type,
                      im.quantity_delta, im.reference_type, im.reference_id,
                      im.notes, im.movement_at
               FROM inventory_movements im
               JOIN batches b ON b.batch_id = im.batch_id
               JOIN drugs d ON d.drug_id = b.drug_id
               WHERE im.movement_at >= %s AND im.movement_at <= %s
               ORDER BY im.movement_at, im.movement_id""",
            (start_at, end_at),
        )
