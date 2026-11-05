
from app.services.batch_service import BatchService


def main():
    service = BatchService()

    try:
        result = service.receive_batch(
            drug_id=1,
            supplier_id=1,
            batch_number="PS061-BATCH-DEMO-001",
            expiry_month="2027-12",
            quantity=100,
            purchase_price="8.00",
            notes="Initial demonstration stock receipt"
        )

        print("\nBATCH RECEIVING SUCCESSFUL")
        print("--------------------------")
        print("Batch ID:", result["batch_id"])
        print("Drug ID:", result["drug_id"])
        print("Supplier ID:", result["supplier_id"])
        print("Batch Number:", result["batch_number"])
        print("Quantity Received:", result["quantity_received"])
        print("Expiry Month:", result["expiry_month"])
        print("Status:", result["status"])

    except ValueError as error:
        print("Validation Error:", error)

    except Exception as error:
        print("Database Error:", error)


if __name__ == "__main__":
    main()
