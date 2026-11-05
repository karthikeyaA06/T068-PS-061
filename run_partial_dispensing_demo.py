
from datetime import date

from app.services.dispensing_service import DispensingService


def main():
    service = DispensingService()

    try:
        result = service.dispense_prescription_line(
            prescription_line_id=2,
            customer_id=1,
            dispense_date=date(2026, 11, 5)
        )

        print("\nPARTIAL DISPENSING RESULT")
        print("-------------------------")
        print("Status:", result["status"])
        print("Dispense ID:", result.get("dispense_id"))
        print("Total dispensed:", result["dispensed_quantity"])
        print("Pending quantity:", result["pending_quantity"])

        print("\nBATCH-WISE ALLOCATION")

        for allocation in result["allocations"]:
            print(
                allocation["batch_number"],
                "| Dispensed:", allocation["quantity"],
                "| Remaining:", allocation["remaining_stock"]
            )

    except Exception as error:
        print("Dispensing failed:", error)


if __name__ == "__main__":
    main()
