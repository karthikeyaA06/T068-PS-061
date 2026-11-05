
class DispensingRepository:
    """Database operations for prescription dispensing."""

    @staticmethod
    def get_prescription_line_for_update(cursor, line_id):
        query = """
            SELECT
                pl.prescription_line_id,
                pl.prescription_id,
                pl.drug_id,
                pl.dose_per_day,
                pl.days_supply,
                pl.required_units,
                pl.dispensed_quantity,
                pl.pending_quantity,
                pl.no_substitution,
                pl.refill_count,
                pl.pending_until,
                pl.status AS line_status,

                p.prescription_date,
                p.patient_id,

                doc.registration_number,
                doc.is_active AS doctor_is_active,

                d.brand_name,
                d.schedule,
                d.pack_size,
                d.sells_full_packs

            FROM prescription_lines pl

            JOIN prescriptions p
                ON pl.prescription_id = p.prescription_id

            JOIN doctors doc
                ON p.doctor_id = doc.doctor_id

            JOIN drugs d
                ON pl.drug_id = d.drug_id

            WHERE pl.prescription_line_id = %s

            FOR UPDATE
        """

        cursor.execute(query, (line_id,))
        return cursor.fetchone()

    @staticmethod
    def get_customer(cursor, customer_id):
        query = """
            SELECT customer_id, loyalty_member
            FROM customers
            WHERE customer_id = %s
        """

        cursor.execute(query, (customer_id,))
        return cursor.fetchone()

    @staticmethod
    def get_batches_for_update(cursor, drug_id):
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
                expiry_month_start,
                received_at,
                batch_number

            FOR UPDATE
        """

        cursor.execute(query, (drug_id,))
        return cursor.fetchall()

    @staticmethod
    def update_batch_stock(cursor, batch_id, new_quantity):
        new_status = "DEPLETED" if new_quantity == 0 else "ACTIVE"

        query = """
            UPDATE batches
            SET
                available_quantity = %s,
                status = %s
            WHERE batch_id = %s
        """

        cursor.execute(
            query,
            (new_quantity, new_status, batch_id)
        )

    @staticmethod
    def create_dispense(cursor, customer_id, prescription_id,
                        patient_id, status):

        query = """
            INSERT INTO dispenses (
                customer_id,
                prescription_id,
                patient_id,
                status
            )
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (customer_id, prescription_id, patient_id, status)
        )

        return cursor.lastrowid

    @staticmethod
    def create_dispense_line(
        cursor,
        dispense_id,
        prescription_line_id,
        drug_id,
        batch_id,
        quantity,
        days_supply,
        brand_name
    ):
        query = """
            INSERT INTO dispense_lines (
                dispense_id,
                prescription_line_id,
                drug_id,
                batch_id,
                quantity,
                days_supply_dispensed,
                is_substituted,
                prescribed_brand,
                dispensed_brand
            )
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, %s)
        """

        cursor.execute(
            query,
            (
                dispense_id,
                prescription_line_id,
                drug_id,
                batch_id,
                quantity,
                days_supply,
                brand_name,
                brand_name
            )
        )

        return cursor.lastrowid

    @staticmethod
    def record_inventory_movement(
        cursor, batch_id, quantity, dispense_id
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
            VALUES (%s, 'DISPENSE', %s, 'DISPENSE', %s, %s)
        """

        cursor.execute(
            query,
            (
                batch_id,
                -quantity,
                str(dispense_id),
                "Prescription dispensing"
            )
        )

    @staticmethod
    def update_prescription_line(
        cursor,
        line_id,
        required_units,
        dispensed_quantity,
        pending_quantity,
        status,
        pending_until
    ):
        query = """
            UPDATE prescription_lines
            SET
                required_units = %s,
                dispensed_quantity = %s,
                pending_quantity = %s,
                status = %s,
                pending_until = %s
            WHERE prescription_line_id = %s
        """

        cursor.execute(
            query,
            (
                required_units,
                dispensed_quantity,
                pending_quantity,
                status,
                pending_until,
                line_id
            )
        )
