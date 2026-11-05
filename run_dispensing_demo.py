
from datetime import date

from app.services.dispensing_service import DispensingService


def main():
    service = DispensingService()

    try:
        result = service.dispense_prescription_line(
            prescription_line_id=1,
            customer_id=1,
            dispense_date=date(2026, 11, 5)
        )

        print("\nDISPENSING TRANSACTION SUCCESSFUL")
        print("--------------------------------")

        print("Status:", result["status"])
        print("Dispense ID:", result.get("dispense_id"))
        print("Dispensed Quantity:", result["dispensed_quantity"])
        print("Pending Quantity:", result["pending_quantity"])

        print("\nBATCH ALLOCATIONS")

        for allocation in result["allocations"]:
            print("Batch:", allocation["batch_number"])
            print("Quantity:", allocation["quantity"])
            print("Remaining Stock:", allocation["remaining_stock"])

    except ValueError as error:
        print("Dispensing Validation Error:", error)

    except Exception as error:
        print("Dispensing Database Error:", error)


if __name__ == "__main__":
    main()
