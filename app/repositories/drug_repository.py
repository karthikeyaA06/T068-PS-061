
class DrugRepository:
    """Handles database operations related to drugs."""

    @staticmethod
    def get_or_create_group(
        cursor,
        molecule,
        strength,
        dosage_form
    ):
        query = """
            INSERT INTO substitution_groups
                (molecule, strength, dosage_form)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                group_id = LAST_INSERT_ID(group_id)
        """

        cursor.execute(
            query,
            (molecule, strength, dosage_form)
        )

        return cursor.lastrowid

    @staticmethod
    def create_drug(cursor, drug_data):
        query = """
            INSERT INTO drugs (
                group_id,
                brand_name,
                schedule,
                mrp,
                gst_rate,
                pack_size,
                min_stock,
                sells_full_packs,
                controlled_substance
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            drug_data["group_id"],
            drug_data["brand_name"],
            drug_data["schedule"],
            drug_data["mrp"],
            drug_data["gst_rate"],
            drug_data["pack_size"],
            drug_data["min_stock"],
            drug_data["sells_full_packs"],
            drug_data["controlled_substance"]
        )

        cursor.execute(query, values)

        return cursor.lastrowid
