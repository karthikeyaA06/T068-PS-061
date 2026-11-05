
class BillingRepository:

    @staticmethod
    def get_dispense_for_update(cursor, dispense_id):
        query = """
            SELECT
                d.dispense_id,
                d.customer_id,
                d.dispensed_at,
                c.loyalty_member
            FROM dispenses d
            JOIN customers c
                ON d.customer_id = c.customer_id
            WHERE d.dispense_id = %s
            FOR UPDATE
        """
        cursor.execute(query, (dispense_id,))
        return cursor.fetchone()

    @staticmethod
    def get_existing_bill(cursor, dispense_id):
        cursor.execute(
            "SELECT bill_id FROM bills WHERE dispense_id = %s",
            (dispense_id,)
        )
        return cursor.fetchone()

    @staticmethod
    def get_billable_lines(cursor, dispense_id):
        query = """
            SELECT
                dl.dispense_line_id,
                dl.drug_id,
                dl.batch_id,
                dl.quantity,
                dl.dispensed_at,
                d.brand_name,
                d.schedule,
                d.mrp,
                d.pack_size,
                d.gst_rate,
                b.expiry_month_start
            FROM dispense_lines dl
            JOIN drugs d ON dl.drug_id = d.drug_id
            JOIN batches b ON dl.batch_id = b.batch_id
            WHERE dl.dispense_id = %s
            ORDER BY dl.dispense_line_id
        """
        cursor.execute(query, (dispense_id,))
        return cursor.fetchall()

    @staticmethod
    def create_bill(cursor, dispense_id, customer_id, totals):
        query = """
            INSERT INTO bills (
                dispense_id,
                customer_id,
                subtotal,
                discount_total,
                gst_total,
                total_before_rounding,
                rounding_adjustment,
                grand_total
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            dispense_id,
            customer_id,
            totals["subtotal"],
            totals["discount_total"],
            totals["gst_total"],
            totals["total_before_rounding"],
            totals["rounding_adjustment"],
            totals["grand_total"]
        ))

        return cursor.lastrowid

    @staticmethod
    def create_bill_line(cursor, bill_id, line):
        query = """
            INSERT INTO bill_lines (
                bill_id,
                dispense_line_id,
                drug_id,
                batch_id,
                quantity,
                mrp_inclusive,
                discount_rate,
                discount_amount,
                gst_rate,
                taxable_value,
                gst_amount,
                line_total
            )
            VALUES (%s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            bill_id,
            line["dispense_line_id"],
            line["drug_id"],
            line["batch_id"],
            line["quantity"],
            line["mrp_inclusive"],
            line["discount_rate"],
            line["discount_amount"],
            line["gst_rate"],
            line["taxable_value"],
            line["gst_amount"],
            line["line_total"]
        ))
