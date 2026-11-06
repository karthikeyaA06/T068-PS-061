
class BatchRepository:
    """Handles database operations for batch inventory."""

    @staticmethod
    def get_active_drug(cursor, drug_id):
        query = """
            SELECT drug_id, pack_size, sells_full_packs
            FROM drugs
            WHERE drug_id = %s AND is_active = TRUE
        """
        cursor.execute(query, (drug_id,))
        return cursor.fetchone()

    @staticmethod
    def get_supplier(cursor, supplier_id):
        query = """
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_id = %s AND is_active = TRUE
        """
        cursor.execute(query, (supplier_id,))
        return cursor.fetchone()

    @staticmethod
    def create_batch(
        cursor,
        drug_id,
        supplier_id,
        batch_number,
        expiry_month_start,
        quantity,
        purchase_price
    ):
        query = """
            INSERT INTO batches (
                drug_id,
                supplier_id,
                batch_number,
                expiry_month_start,
                received_quantity,
                available_quantity,
                purchase_price,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
        """

        cursor.execute(
            query,
            (
                drug_id,
                supplier_id,
                batch_number,
                expiry_month_start,
                quantity,
                quantity,
                purchase_price
            )
        )

        return cursor.lastrowid

    @staticmethod
    def record_stock_receipt(
        cursor,
        batch_id,
        quantity,
        notes=None
    ):
        query = """
            INSERT INTO inventory_movements (
                batch_id,
                movement_type,
                quantity_delta,
                reference_type,
                reference_id,
                notes
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                batch_id,
                "RECEIPT",
                quantity,
                "BATCH",
                str(batch_id),
                notes
            )
        )


    @staticmethod
    def get_active_batches_for_drug(cursor, drug_id):
        """Fetch all active batches with available stock."""

        query = """
            SELECT
                batch_id,
                batch_number,
                expiry_month_start,
                received_at,
                b.available_quantity,
                COALESCE(sr.reserved_quantity, 0) AS reserved_quantity,
                b.status
            FROM batches b
            LEFT JOIN (
                SELECT batch_id, SUM(quantity) AS reserved_quantity
                FROM supplier_returns
                WHERE status = 'PENDING'
                GROUP BY batch_id
            ) sr ON sr.batch_id = b.batch_id
            WHERE b.drug_id = %s
              AND b.status = 'ACTIVE'
              AND b.available_quantity > COALESCE(sr.reserved_quantity, 0)
            ORDER BY
                b.expiry_month_start ASC,
                b.received_at ASC,
                b.batch_number ASC
        """

        cursor.execute(query, (drug_id,))
        return cursor.fetchall()
