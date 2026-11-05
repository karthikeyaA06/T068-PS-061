
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
                available_quantity,
                status
            FROM batches
            WHERE drug_id = %s
              AND status = 'ACTIVE'
              AND available_quantity > 0
            ORDER BY
                expiry_month_start ASC,
                received_at ASC,
                batch_number ASC
        """

        cursor.execute(query, (drug_id,))
        return cursor.fetchall()
