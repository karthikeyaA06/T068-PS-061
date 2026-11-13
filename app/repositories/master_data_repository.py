class MasterDataRepository:
    """Parameterized inserts and lookups for pharmacy master data."""

    @staticmethod
    def create_supplier(cursor, supplier_name, contact_person=None, phone=None, email=None, address=None):
        cursor.execute(
            """INSERT INTO suppliers
               (supplier_name, contact_person, phone, email, address)
               VALUES (%s, %s, %s, %s, %s)""",
            (supplier_name, contact_person, phone, email, address),
        )
        return cursor.lastrowid

    @staticmethod
    def create_customer(cursor, customer_name, phone=None, loyalty_member=False):
        cursor.execute(
            """INSERT INTO customers (customer_name, phone, loyalty_member)
               VALUES (%s, %s, %s)""",
            (customer_name, phone, loyalty_member),
        )
        return cursor.lastrowid

    @staticmethod
    def create_doctor(cursor, registration_number, doctor_name, is_active=True):
        cursor.execute(
            """INSERT INTO doctors (registration_number, doctor_name, is_active)
               VALUES (%s, %s, %s)""",
            (registration_number, doctor_name, is_active),
        )
        return cursor.lastrowid

    @staticmethod
    def create_patient(cursor, patient_name, contact=None):
        cursor.execute(
            "INSERT INTO patients (patient_name, contact) VALUES (%s, %s)",
            (patient_name, contact),
        )
        return cursor.lastrowid
