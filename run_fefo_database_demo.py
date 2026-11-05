
from datetime import date

from app.services.inventory_service import InventoryService
from app.services.fefo_service import FEFOSelector


def main():
    service = InventoryService()

    # Fixed date makes this demonstration reproducible.
    dispense_date = date(2026, 11, 5)

    try:
        batches = service.get_fefo_batches(
            drug_id=1,
            dispense_date=dispense_date,
            days_supply=10
        )

        print("\nFEFO DATABASE SELECTION")
        print("-----------------------")
        print("Drug ID: 1")
        print("Dispense date:", dispense_date)
        print("Prescription supply: 10 days")

        if not batches:
            print("No eligible batches found.")
            return

        for position, batch in enumerate(batches, start=1):
            expiry = FEFOSelector.get_expiry_date(
                batch.expiry_month_start
            )

            days_left = FEFOSelector.days_until_expiry(
                batch, dispense_date
            )

            print(f"\nPriority: {position}")
            print("Batch ID:", batch.batch_id)
            print("Batch number:", batch.batch_number)
            print("Expiry date:", expiry)
            print("Available units:", batch.available_quantity)
            print("Days until expiry:", days_left)
            print(
                "Near expiry:",
                FEFOSelector.is_near_expiry(batch, dispense_date)
            )

    except Exception as error:
        print("FEFO database test failed:", error)


if __name__ == "__main__":
    main()
