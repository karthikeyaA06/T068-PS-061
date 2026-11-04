
from decimal import Decimal, InvalidOperation

import mysql.connector

from app.database.connection import get_connection
from app.repositories.drug_repository import DrugRepository


class DrugService:
    """Implements drug registration and validation."""

    VALID_SCHEDULES = {"NONE", "H", "H1", "X"}
    VALID_GST_RATES = {Decimal("5.00"), Decimal("12.00")}

    @staticmethod
    def _validate_text(value, field_name):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} is required.")

        return value.strip()

    @staticmethod
    def _validate_decimal(value, field_name):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{field_name} must be a valid number.")

        if not result.is_finite():
            raise ValueError(f"{field_name} must be finite.")

        return result

    @staticmethod
    def _validate_integer(value, field_name, minimum):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field_name} must be an integer.")

        if value < minimum:
            raise ValueError(
                f"{field_name} must be at least {minimum}."
            )

        return value

    def register_drug(
        self,
        molecule,
        strength,
        dosage_form,
        brand_name,
        schedule,
        mrp,
        gst_rate,
        pack_size,
        min_stock,
        sells_full_packs=False,
        controlled_substance=False
    ):
        # -------------------------------
        # 1. Validate text fields
        # -------------------------------

        molecule = self._validate_text(molecule, "Molecule")
        strength = self._validate_text(strength, "Strength")
        dosage_form = self._validate_text(
            dosage_form, "Dosage form"
        )
        brand_name = self._validate_text(brand_name, "Brand name")

        schedule = self._validate_text(
            schedule, "Schedule"
        ).upper()

        # -------------------------------
        # 2. Validate schedule
        # -------------------------------

        if schedule not in self.VALID_SCHEDULES:
            raise ValueError(
                "Schedule must be NONE, H, H1 or X."
            )

        # -------------------------------
        # 3. Validate MRP
        # -------------------------------

        mrp = self._validate_decimal(mrp, "MRP")

        if mrp <= 0:
            raise ValueError("MRP must be greater than zero.")

        # -------------------------------
        # 4. Validate GST
        # -------------------------------

        gst_rate = self._validate_decimal(
            gst_rate, "GST rate"
        )

        if gst_rate not in self.VALID_GST_RATES:
            raise ValueError("GST must be either 5% or 12%.")

        # -------------------------------
        # 5. Validate quantities
        # -------------------------------

        pack_size = self._validate_integer(
            pack_size, "Pack size", 1
        )

        min_stock = self._validate_integer(
            min_stock, "Minimum stock", 0
        )

        if not isinstance(sells_full_packs, bool):
            raise ValueError(
                "sells_full_packs must be True or False."
            )

        if not isinstance(controlled_substance, bool):
            raise ValueError(
                "controlled_substance must be True or False."
            )

        drug_data = {
            "brand_name": brand_name,
            "schedule": schedule,
            "mrp": mrp,
            "gst_rate": gst_rate,
            "pack_size": pack_size,
            "min_stock": min_stock,
            "sells_full_packs": sells_full_packs,
            "controlled_substance": controlled_substance
        }

        connection = None
        cursor = None

        try:
            # -------------------------------
            # 6. Connect to MySQL
            # -------------------------------

            connection = get_connection()
            connection.start_transaction()

            cursor = connection.cursor()

            # -------------------------------
            # 7. Find or create substitution group
            # -------------------------------

            group_id = DrugRepository.get_or_create_group(
                cursor,
                molecule,
                strength,
                dosage_form
            )

            drug_data["group_id"] = group_id

            # -------------------------------
            # 8. Register drug
            # -------------------------------

            drug_id = DrugRepository.create_drug(
                cursor,
                drug_data
            )

            # -------------------------------
            # 9. Commit transaction
            # -------------------------------

            connection.commit()

            return {
                "drug_id": drug_id,
                "group_id": group_id,
                "brand_name": brand_name,
                "status": "REGISTERED"
            }

        except mysql.connector.IntegrityError as error:

            if connection and connection.is_connected():
                connection.rollback()

            if error.errno == 1062:
                raise ValueError(
                    f"Brand '{brand_name}' is already registered "
                    "in this substitution group."
                ) from error

            raise

        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise

        finally:
            if cursor is not None:
                cursor.close()

            if connection is not None and connection.is_connected():
                connection.close()
