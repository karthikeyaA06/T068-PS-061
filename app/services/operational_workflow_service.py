"""Transactional MySQL workflows for returns, recalls, write-offs and reorders."""

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.database.connection import get_connection
from app.services.fefo_service import FEFOSelector
from app.services.operational_rules_service import OperationalRulesService


class OperationalWorkflowService:
    CENT = Decimal("0.01")

    @staticmethod
    def _now(value=None):
        value = value or datetime.now()
        if not isinstance(value, datetime):
            raise ValueError("A datetime value is required.")
        return value

    @staticmethod
    def _positive_int(value, name):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")
        return value

    def process_customer_return(
        self, bill_line_id, quantity, unopened, returned_at=None
    ):
        """Restore eligible returned quantity to the exact original batch."""
        self._positive_int(bill_line_id, "bill_line_id")
        self._positive_int(quantity, "quantity")
        if not isinstance(unopened, bool):
            raise ValueError("unopened must be boolean.")
        returned_at = self._now(returned_at)
        connection = cursor = None
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT bl.bill_line_id, bl.bill_id, bl.quantity AS billed_quantity,
                       bl.line_total, dp.dispensed_at, d.schedule,
                       b.batch_id, b.available_quantity, b.status,
                       b.expiry_month_start
                FROM bill_lines bl
                JOIN bills bh ON bh.bill_id = bl.bill_id
                JOIN dispense_lines dl ON dl.dispense_line_id = bl.dispense_line_id
                JOIN dispenses dp ON dp.dispense_id = dl.dispense_id
                JOIN drugs d ON d.drug_id = bl.drug_id
                JOIN batches b ON b.batch_id = bl.batch_id
                WHERE bl.bill_line_id = %s
                FOR UPDATE
                """,
                (bill_line_id,),
            )
            line = cursor.fetchone()
            if line is None:
                raise ValueError("ORIGINAL_BILL_LINE_NOT_FOUND")
            cursor.execute(
                "SELECT COALESCE(SUM(quantity), 0) AS returned_qty "
                "FROM customer_returns WHERE bill_line_id = %s",
                (bill_line_id,),
            )
            already_returned = int(cursor.fetchone()["returned_qty"])
            remaining = int(line["billed_quantity"]) - already_returned
            if quantity > remaining:
                raise ValueError("RETURN_QUANTITY_EXCEEDS_SOLD_QUANTITY")

            expiry_date = FEFOSelector.get_expiry_date(line["expiry_month_start"])
            days_to_expiry = (expiry_date - returned_at.date()).days
            decision = OperationalRulesService.validate_customer_return(
                sale_datetime=line["dispensed_at"],
                return_datetime=returned_at,
                original_bill_present=True,
                unopened=unopened,
                schedule=line["schedule"],
                days_to_expiry=days_to_expiry,
                original_billed_amount=Decimal(str(line["line_total"]))
                * Decimal(quantity) / Decimal(line["billed_quantity"]),
            )
            refund = decision["refund_amount"].quantize(self.CENT, rounding=ROUND_HALF_UP)
            cursor.execute(
                """INSERT INTO customer_returns
                   (bill_line_id, batch_id, quantity, refund_amount, unopened, returned_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (bill_line_id, line["batch_id"], quantity, refund, unopened, returned_at),
            )
            new_stock = int(line["available_quantity"]) + quantity
            new_status = "ACTIVE" if line["status"] == "DEPLETED" else line["status"]
            cursor.execute(
                "UPDATE batches SET available_quantity = %s, status = %s WHERE batch_id = %s",
                (new_stock, new_status, line["batch_id"]),
            )
            cursor.execute(
                """INSERT INTO inventory_movements
                   (batch_id, movement_type, quantity_delta, reference_type, reference_id, notes)
                   VALUES (%s, 'CUSTOMER_RETURN', %s, 'CUSTOMER_RETURN', %s, %s)""",
                (line["batch_id"], quantity, str(bill_line_id), "Customer return restored to original batch"),
            )
            connection.commit()
            return {
                "status": "RETURN_ACCEPTED",
                "bill_line_id": bill_line_id,
                "batch_id": line["batch_id"],
                "quantity_restored": quantity,
                "refund_amount": refund,
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

    def request_supplier_return(self, batch_id, quantity=None, reason="Supplier return", requested_at=None):
        """Reserve stock for a pending supplier return; it cannot be dispensed/reordered."""
        self._positive_int(batch_id, "batch_id")
        requested_at = self._now(requested_at)
        reason = str(reason).strip()
        if not reason:
            raise ValueError("A supplier-return reason is required.")
        connection = cursor = None
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT batch_id, supplier_id, expiry_month_start,
                          available_quantity, status
                   FROM batches WHERE batch_id = %s FOR UPDATE""",
                (batch_id,),
            )
            batch = cursor.fetchone()
            if batch is None:
                raise ValueError("BATCH_NOT_FOUND")
            cursor.execute(
                "SELECT COALESCE(SUM(quantity),0) AS pending_qty FROM supplier_returns "
                "WHERE batch_id = %s AND status = 'PENDING'",
                (batch_id,),
            )
            reserved = int(cursor.fetchone()["pending_qty"])
            saleable = int(batch["available_quantity"]) - reserved
            if quantity is None:
                quantity = saleable
            self._positive_int(quantity, "quantity")
            if quantity > saleable:
                raise ValueError("RETURN_QUANTITY_EXCEEDS_AVAILABLE_STOCK")
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM dispense_lines WHERE batch_id = %s) AS ever_dispensed",
                (batch_id,),
            )
            ever_dispensed = bool(cursor.fetchone()["ever_dispensed"])
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM batch_recalls WHERE batch_id = %s) AS recalled",
                (batch_id,),
            )
            recalled = bool(cursor.fetchone()["recalled"])
            expiry_date = FEFOSelector.get_expiry_date(batch["expiry_month_start"])
            days_to_expiry = (expiry_date - requested_at.date()).days
            if not OperationalRulesService.supplier_return_allowed(days_to_expiry, ever_dispensed, recalled):
                raise ValueError("SUPPLIER_RETURN_NOT_ELIGIBLE")
            cursor.execute(
                """INSERT INTO supplier_returns
                   (batch_id, supplier_id, quantity, reason, status, requested_at)
                   VALUES (%s, %s, %s, %s, 'PENDING', %s)""",
                (batch_id, batch["supplier_id"], quantity, reason, requested_at),
            )
            return_id = cursor.lastrowid
            connection.commit()
            return {"supplier_return_id": return_id, "status": "PENDING", "quantity_reserved": quantity}
        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def complete_supplier_return(self, supplier_return_id, completed_at=None):
        self._positive_int(supplier_return_id, "supplier_return_id")
        completed_at = self._now(completed_at)
        connection = cursor = None
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT sr.*, b.available_quantity, b.status AS batch_status
                   FROM supplier_returns sr JOIN batches b ON b.batch_id = sr.batch_id
                   WHERE sr.supplier_return_id = %s FOR UPDATE""",
                (supplier_return_id,),
            )
            row = cursor.fetchone()
            if not row or row["status"] != "PENDING":
                raise ValueError("PENDING_SUPPLIER_RETURN_NOT_FOUND")
            new_qty = int(row["available_quantity"]) - int(row["quantity"])
            if new_qty < 0:
                raise ValueError("SUPPLIER_RETURN_EXCEEDS_BATCH_STOCK")
            new_status = "RETURNED" if new_qty == 0 else row["batch_status"]
            cursor.execute(
                "UPDATE batches SET available_quantity = %s, status = %s WHERE batch_id = %s",
                (new_qty, new_status, row["batch_id"]),
            )
            cursor.execute(
                """INSERT INTO inventory_movements
                   (batch_id, movement_type, quantity_delta, reference_type, reference_id, notes)
                   VALUES (%s, 'SUPPLIER_RETURN', %s, 'SUPPLIER_RETURN', %s, %s)""",
                (row["batch_id"], -int(row["quantity"]), str(supplier_return_id), row["reason"]),
            )
            cursor.execute(
                "UPDATE supplier_returns SET status = 'COMPLETED', completed_at = %s "
                "WHERE supplier_return_id = %s",
                (completed_at, supplier_return_id),
            )
            connection.commit()
            return {"supplier_return_id": supplier_return_id, "status": "COMPLETED", "stock_remaining": new_qty}
        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def cancel_supplier_return(self, supplier_return_id):
        """Cancel a pending supplier return and release its reserved stock."""
        self._positive_int(supplier_return_id, "supplier_return_id")
        connection = cursor = None
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT supplier_return_id, status FROM supplier_returns "
                "WHERE supplier_return_id = %s FOR UPDATE",
                (supplier_return_id,),
            )
            row = cursor.fetchone()
            if not row or row["status"] != "PENDING":
                raise ValueError("PENDING_SUPPLIER_RETURN_NOT_FOUND")
            cursor.execute(
                "UPDATE supplier_returns SET status = 'CANCELLED' "
                "WHERE supplier_return_id = %s",
                (supplier_return_id,),
            )
            connection.commit()
            return {"supplier_return_id": supplier_return_id, "status": "CANCELLED"}
        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def recall_batch(self, batch_id, reason, recalled_at=None):
        self._positive_int(batch_id, "batch_id")
        reason = str(reason).strip()
        if not reason:
            raise ValueError("A recall reason is required.")
        recalled_at = self._now(recalled_at)
        connection = cursor = None
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT batch_id, available_quantity FROM batches WHERE batch_id = %s FOR UPDATE", (batch_id,))
            batch = cursor.fetchone()
            if not batch:
                raise ValueError("BATCH_NOT_FOUND")
            cursor.execute(
                "INSERT INTO batch_recalls (batch_id, reason, recalled_at) VALUES (%s, %s, %s)",
                (batch_id, reason, recalled_at),
            )
            recall_id = cursor.lastrowid
            cursor.execute("UPDATE batches SET status = 'FROZEN' WHERE batch_id = %s", (batch_id,))
            cursor.execute(
                """INSERT INTO inventory_movements
                   (batch_id, movement_type, quantity_delta, reference_type, reference_id, notes, movement_at)
                   VALUES (%s, 'RECALL', 0, 'RECALL', %s, %s, %s)""",
                (batch_id, str(recall_id), reason, recalled_at),
            )
            connection.commit()
            return {"recall_id": recall_id, "batch_id": batch_id, "status": "FROZEN", "recalled_at": recalled_at}
        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def get_recall_violations(self, recall_id):
        self._positive_int(recall_id, "recall_id")
        connection = cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT br.recall_id, br.batch_id, br.recalled_at,
                          dl.dispense_line_id, dp.dispense_id, dp.dispensed_at,
                          dl.quantity
                   FROM batch_recalls br
                   JOIN dispense_lines dl ON dl.batch_id = br.batch_id
                   JOIN dispenses dp ON dp.dispense_id = dl.dispense_id
                   WHERE br.recall_id = %s AND dp.dispensed_at > br.recalled_at
                   ORDER BY dp.dispensed_at""",
                (recall_id,),
            )
            return cursor.fetchall()
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def run_end_of_day(self, business_date):
        """Flag near-expiry stock, write off expired batches, and save reorder suggestions."""
        if isinstance(business_date, datetime):
            business_date = business_date.date()
        if not isinstance(business_date, date):
            raise ValueError("business_date must be a date.")
        connection = cursor = None
        written_off, near_expiry, reorders, deferred_writeoffs = [], [], [], []
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """SELECT b.batch_id, b.drug_id, b.batch_number, b.expiry_month_start,
                          b.available_quantity, b.purchase_price, b.status
                   FROM batches b WHERE b.status IN ('ACTIVE','FROZEN')
                   AND b.available_quantity > 0 FOR UPDATE"""
            )
            batch_rows = cursor.fetchall()
            for batch in batch_rows:
                expiry = FEFOSelector.get_expiry_date(batch["expiry_month_start"])
                days_left = (expiry - business_date).days
                if batch["status"] == "ACTIVE" and OperationalRulesService.is_near_expiry(days_left):
                    near_expiry.append({"batch_id": batch["batch_id"], "batch_number": batch["batch_number"], "days_to_expiry": days_left})
                if batch["status"] in {"ACTIVE", "FROZEN"} and OperationalRulesService.is_expired(expiry, business_date):
                    cursor.execute(
                        "SELECT COALESCE(SUM(quantity),0) AS reserved_qty FROM supplier_returns "
                        "WHERE batch_id = %s AND status = 'PENDING'",
                        (batch["batch_id"],),
                    )
                    reserved_qty = int(cursor.fetchone()["reserved_qty"] or 0)
                    if reserved_qty:
                        # An expired batch with an outstanding supplier return must
                        # not remain sellable while the return is reconciled.
                        cursor.execute(
                            "UPDATE batches SET status = 'FROZEN' WHERE batch_id = %s",
                            (batch["batch_id"],),
                        )
                        deferred_writeoffs.append({"batch_id": batch["batch_id"], "pending_supplier_return_quantity": reserved_qty})
                        continue
                    qty = int(batch["available_quantity"])
                    if qty <= 0:
                        continue
                    amount = OperationalRulesService.calculate_writeoff_value(qty, batch["purchase_price"])
                    cursor.execute(
                        """INSERT INTO batch_writeoffs
                           (batch_id, quantity, purchase_price_per_unit, writeoff_value, business_date)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (batch["batch_id"], qty, batch["purchase_price"], amount, business_date),
                    )
                    writeoff_id = cursor.lastrowid
                    cursor.execute(
                        "UPDATE batches SET available_quantity = 0, status = 'WRITTEN_OFF' WHERE batch_id = %s",
                        (batch["batch_id"],),
                    )
                    cursor.execute(
                        """INSERT INTO inventory_movements
                           (batch_id, movement_type, quantity_delta, reference_type, reference_id, notes)
                           VALUES (%s, 'WRITE_OFF', %s, 'WRITE_OFF', %s, %s)""",
                        (batch["batch_id"], -qty, str(writeoff_id), f"Expired stock write-off on {business_date}"),
                    )
                    written_off.append({"batch_id": batch["batch_id"], "quantity": qty, "value": amount})

            cursor.execute("SELECT drug_id, min_stock, pack_size FROM drugs WHERE is_active = TRUE ORDER BY drug_id")
            for drug in cursor.fetchall():
                cursor.execute(
                    """SELECT COALESCE(SUM(b.available_quantity - COALESCE(sr.reserved_quantity,0)),0) AS valid_stock,
                              COALESCE(SUM(CASE WHEN sr.reserved_quantity > 0 THEN 1 ELSE 0 END),0) AS batches_with_pending_returns,
                              MAX(CASE WHEN sr.reserved_quantity > 0 THEN 1 ELSE 0 END) AS has_pending_return
                       FROM batches b
                       LEFT JOIN (
                           SELECT batch_id, SUM(quantity) AS reserved_quantity
                           FROM supplier_returns WHERE status = 'PENDING' GROUP BY batch_id
                       ) sr ON sr.batch_id = b.batch_id
                       WHERE b.drug_id = %s AND b.status = 'ACTIVE'
                         AND LAST_DAY(b.expiry_month_start) >= %s""",
                    (drug["drug_id"], business_date),
                )
                stock_row = cursor.fetchone()
                valid_stock = int(stock_row["valid_stock"] or 0)
                has_pending = bool(stock_row["has_pending_return"])
                if has_pending:
                    continue
                qty = OperationalRulesService.calculate_reorder_quantity(
                    valid_stock, int(drug["min_stock"]), int(drug["pack_size"]), False
                )
                if qty > 0:
                    cursor.execute(
                        """INSERT INTO reorder_suggestions
                           (drug_id, business_date, valid_stock, minimum_stock, reorder_quantity)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE valid_stock = VALUES(valid_stock),
                             minimum_stock = VALUES(minimum_stock), reorder_quantity = VALUES(reorder_quantity)""",
                        (drug["drug_id"], business_date, valid_stock, drug["min_stock"], qty),
                    )
                    reorders.append({"drug_id": drug["drug_id"], "valid_stock": valid_stock, "reorder_quantity": qty})
            connection.commit()
            return {
                "business_date": business_date,
                "near_expiry": near_expiry,
                "written_off": written_off,
                "deferred_writeoffs": deferred_writeoffs,
                "reorders": reorders,
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
