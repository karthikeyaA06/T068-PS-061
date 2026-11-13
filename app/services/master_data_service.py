"""Create supplier, customer, doctor and patient master records."""

from app.database.connection import get_connection
from app.repositories.master_data_repository import MasterDataRepository


class MasterDataService:
    @staticmethod
    def _required_text(value, name, max_length):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required.")
        value = value.strip()
        if len(value) > max_length:
            raise ValueError(f"{name} must be at most {max_length} characters.")
        return value

    @staticmethod
    def _optional_text(value, name, max_length):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{name} must be text.")
        value = value.strip()
        if not value:
            return None
        if len(value) > max_length:
            raise ValueError(f"{name} must be at most {max_length} characters.")
        return value

    @staticmethod
    def _insert(operation, *args):
        connection = cursor = None
        try:
            connection = get_connection()
            connection.start_transaction()
            cursor = connection.cursor()
            record_id = operation(cursor, *args)
            connection.commit()
            return record_id
        except Exception:
            if connection and connection.is_connected():
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    def register_supplier(
        self, supplier_name, contact_person=None, phone=None, email=None, address=None
    ):
        supplier_name = self._required_text(supplier_name, "supplier_name", 200)
        contact_person = self._optional_text(contact_person, "contact_person", 150)
        phone = self._optional_text(phone, "phone", 20)
        email = self._optional_text(email, "email", 150)
        address = self._optional_text(address, "address", 10000)
        supplier_id = self._insert(
            MasterDataRepository.create_supplier,
            supplier_name, contact_person, phone, email, address,
        )
        return {"supplier_id": supplier_id, "supplier_name": supplier_name}

    def register_customer(self, customer_name, phone=None, loyalty_member=False):
        customer_name = self._required_text(customer_name, "customer_name", 150)
        phone = self._optional_text(phone, "phone", 20)
        if not isinstance(loyalty_member, bool):
            raise ValueError("loyalty_member must be boolean.")
        customer_id = self._insert(
            MasterDataRepository.create_customer,
            customer_name, phone, loyalty_member,
        )
        return {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "loyalty_member": loyalty_member,
        }

    def register_doctor(self, registration_number, doctor_name, is_active=True):
        registration_number = self._required_text(
            registration_number, "registration_number", 100
        )
        doctor_name = self._required_text(doctor_name, "doctor_name", 150)
        if not isinstance(is_active, bool):
            raise ValueError("is_active must be boolean.")
        doctor_id = self._insert(
            MasterDataRepository.create_doctor,
            registration_number, doctor_name, is_active,
        )
        return {
            "doctor_id": doctor_id,
            "registration_number": registration_number,
            "doctor_name": doctor_name,
            "is_active": is_active,
        }

    def register_patient(self, patient_name, contact=None):
        patient_name = self._required_text(patient_name, "patient_name", 150)
        contact = self._optional_text(contact, "contact", 20)
        patient_id = self._insert(
            MasterDataRepository.create_patient, patient_name, contact
        )
        return {"patient_id": patient_id, "patient_name": patient_name}
