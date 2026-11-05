
class DispensingRepository:
    """Database operations for prescription dispensing and compliance."""

    @staticmethod
    def lock_patient(cursor, patient_id):
        cursor.execute(
            """
            SELECT patient_id
            FROM patients
            WHERE patient_id = %s
            FOR UPDATE
            """,
            (patient_id,)
        )

        if cursor.fetchone() is None:
            raise ValueError("Patient not found.")

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

                pat.patient_name,

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

            JOIN patients pat
                ON p.patient_id = pat.patient_id

            JOIN drugs d
                ON pl.drug_id = d.drug_id

            WHERE pl.prescription_line_id = %s

            FOR UPDATE
        """

        cursor.execute(query, (line_id,))
        return cursor.fetchone()

    @staticmethod
    def get_customer(cursor, customer_id):
        cursor.execute(
            """
            SELECT customer_id, loyalty_member
            FROM customers
            WHERE customer_id = %s
            """,
            (customer_id,)
        )

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
    def get_prior_days_supply(
        cursor,
        patient_id,
        drug_id,
        window_start,
        window_end
    ):
        query = """
            SELECT COALESCE(
                SUM(dl.days_supply_dispensed), 0
            ) AS prior_days_supply
            FROM dispense_lines dl
            JOIN dispenses dp
                ON dl.dispense_id = dp.dispense_id
            WHERE dp.patient_id = %s
              AND dl.drug_id = %s
              AND dp.dispensed_at >= %s
              AND dp.dispensed_at <= %s
        """

        cursor.execute(
            query,
            (patient_id, drug_id, window_start, window_end)
        )

        return cursor.fetchone()["prior_days_supply"]

    @staticmethod
    def get_first_dispensed_at(cursor, prescription_line_id):
        query = """
            SELECT MIN(dp.dispensed_at) AS first_dispensed_at
            FROM dispense_lines dl
            JOIN dispenses dp
                ON dl.dispense_id = dp.dispense_id
            WHERE dl.prescription_line_id = %s
        """

        cursor.execute(query, (prescription_line_id,))
        return cursor.fetchone()["first_dispensed_at"]

    @staticmethod
    def update_batch_stock(cursor, batch_id, new_quantity):
        status = (
            "DEPLETED" if new_quantity == 0 else "ACTIVE"
        )

        cursor.execute(
            """
            UPDATE batches
            SET available_quantity = %s,
                status = %s
            WHERE batch_id = %s
            """,
            (new_quantity, status, batch_id)
        )

    @staticmethod
    def create_dispense(
        cursor,
        customer_id,
        prescription_id,
        patient_id,
        dispensed_at,
        status
    ):
        cursor.execute(
            """
            INSERT INTO dispenses (
                customer_id,
                prescription_id,
                patient_id,
                dispensed_at,
                status
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                customer_id,
                prescription_id,
                patient_id,
                dispensed_at,
                status
            )
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
        brand_name,
        dispensed_at
    ):
        cursor.execute(
            """
            INSERT INTO dispense_lines (
                dispense_id,
                prescription_line_id,
                drug_id,
                batch_id,
                quantity,
                days_supply_dispensed,
                is_substituted,
                prescribed_brand,
                dispensed_brand,
                dispensed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s)
            """,
            (
                dispense_id,
                prescription_line_id,
                drug_id,
                batch_id,
                quantity,
                days_supply,
                brand_name,
                brand_name,
                dispensed_at
            )
        )

        return cursor.lastrowid

    @staticmethod
    def record_inventory_movement(
        cursor,
        batch_id,
        quantity,
        dispense_id
    ):
        cursor.execute(
            """
            INSERT INTO inventory_movements (
                batch_id,
                movement_type,
                quantity_delta,
                reference_type,
                reference_id,
                notes
            )
            VALUES (%s, 'DISPENSE', %s, 'DISPENSE', %s, %s)
            """,
            (
                batch_id,
                -quantity,
                str(dispense_id),
                "Prescription dispensing"
            )
        )

    @staticmethod
    def record_h1_register(
        cursor,
        dispense_line_id,
        patient_name,
        doctor_registration_number,
        dispense_date,
        quantity
    ):
        cursor.execute(
            """
            INSERT INTO h1_register_entries (
                dispense_line_id,
                patient_name,
                doctor_registration_number,
                dispense_date,
                quantity
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                dispense_line_id,
                patient_name,
                doctor_registration_number,
                dispense_date,
                quantity
            )
        )

    @staticmethod
    def record_x_register(
        cursor,
        dispense_line_id,
        patient_name,
        doctor_registration_number,
        batch_number,
        dispense_date,
        quantity
    ):
        cursor.execute(
            """
            INSERT INTO x_register_entries (
                dispense_line_id,
                patient_name,
                doctor_registration_number,
                batch_number,
                dispense_date,
                quantity
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                dispense_line_id,
                patient_name,
                doctor_registration_number,
                batch_number,
                dispense_date,
                quantity
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
        pending_until,
        refill_count
    ):
        cursor.execute(
            """
            UPDATE prescription_lines
            SET required_units = %s,
                dispensed_quantity = %s,
                pending_quantity = %s,
                status = %s,
                pending_until = %s,
                refill_count = %s
            WHERE prescription_line_id = %s
            """,
            (
                required_units,
                dispensed_quantity,
                pending_quantity,
                status,
                pending_until,
                refill_count,
                line_id
            )
        )
