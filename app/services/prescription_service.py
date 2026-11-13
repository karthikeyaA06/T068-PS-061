"""Prescription intake and line creation (BR-02, BR-03, BR-12)."""

from datetime import date, datetime
from decimal import Decimal

from app.database.connection import get_connection
from app.services.quantity_service import QuantityService
from app.services.compliance_service import PrescriptionComplianceService


class PrescriptionService:
    @staticmethod
    def calculate_required_units(dose_per_day, days_supply, pack_size, sells_full_packs):
        return QuantityService.required_units(
            dose_per_day, days_supply, pack_size, sells_full_packs
        )

    @staticmethod
    def _positive_id(value, name):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")
        return value

    def create_prescription(self, doctor_id, patient_id, prescription_date, lines):
        doctor_id = self._positive_id(doctor_id, "doctor_id")
        patient_id = self._positive_id(patient_id, "patient_id")
        if isinstance(prescription_date, datetime):
            prescription_date = prescription_date.date()
        if not isinstance(prescription_date, date):
            raise ValueError("prescription_date must be an ISO date.")
        if not isinstance(lines, list) or not lines:
            raise ValueError("lines must be a non-empty list.")

        prepared = []
        for index, line in enumerate(lines, start=1):
            if not isinstance(line, dict):
                raise ValueError(f"Line {index} must be an object.")
            drug_id = self._positive_id(line.get("drug_id"), f"lines[{index}].drug_id")
            dose = line.get("dose_per_day")
            days = line.get("days_supply")
            no_substitution = line.get("no_substitution", False)
            if not isinstance(no_substitution, bool):
                raise ValueError(f"lines[{index}].no_substitution must be boolean.")
            prepared.append({
                "drug_id": drug_id,
                "dose_per_day": dose,
                "days_supply": days,
                "no_substitution": no_substitution,
            })

        connection = cursor = None
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT doctor_id, registration_number, is_active FROM doctors WHERE doctor_id = %s FOR UPDATE",
                (doctor_id,),
            )
            doctor = cursor.fetchone()
            if doctor is None or not doctor["is_active"] or not str(doctor["registration_number"]).strip():
                raise ValueError("INVALID_DOCTOR_REGISTRATION")

            cursor.execute(
                "SELECT patient_id FROM patients WHERE patient_id = %s FOR UPDATE",
                (patient_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("PATIENT_NOT_FOUND")

            cursor.execute(
                "INSERT INTO prescriptions (doctor_id, patient_id, prescription_date) VALUES (%s, %s, %s)",
                (doctor_id, patient_id, prescription_date),
            )
            prescription_id = cursor.lastrowid
            created_lines = []

            for line in prepared:
                cursor.execute(
                    """SELECT drug_id, pack_size, sells_full_packs, is_active, schedule
                       FROM drugs WHERE drug_id = %s FOR UPDATE""",
                    (line["drug_id"],),
                )
                drug = cursor.fetchone()
                if drug is None or not drug["is_active"]:
                    raise ValueError(f"ACTIVE_DRUG_NOT_FOUND:{line['drug_id']}")

                # Validate prescription age and Schedule X limits at intake,
                # not only later when the cashier attempts to dispense.
                PrescriptionComplianceService.validate_prescription(
                    schedule=drug["schedule"],
                    prescription_date=prescription_date,
                    dispense_date=date.today(),
                    doctor_registration_number=doctor["registration_number"],
                    doctor_is_active=bool(doctor["is_active"]),
                    days_supply=line["days_supply"],
                    refill_count=0,
                )

                required_units = self.calculate_required_units(
                    line["dose_per_day"],
                    line["days_supply"],
                    int(drug["pack_size"]),
                    bool(drug["sells_full_packs"]),
                )
                cursor.execute(
                    """INSERT INTO prescription_lines
                       (prescription_id, drug_id, dose_per_day, days_supply,
                        required_units, no_substitution)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        prescription_id,
                        line["drug_id"],
                        str(Decimal(str(line["dose_per_day"]))),
                        line["days_supply"],
                        required_units,
                        line["no_substitution"],
                    ),
                )
                created_lines.append({
                    "prescription_line_id": cursor.lastrowid,
                    "drug_id": line["drug_id"],
                    "required_units": required_units,
                    "days_supply": line["days_supply"],
                    "status": "NEW",
                })

            connection.commit()
            return {
                "prescription_id": prescription_id,
                "doctor_id": doctor_id,
                "patient_id": patient_id,
                "prescription_date": prescription_date,
                "lines": created_lines,
                "status": "ACTIVE",
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
