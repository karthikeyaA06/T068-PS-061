
import sys

from app.services.billing_service import BillingService


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python run_billing_demo.py <dispense_id>"
        )
        return

    try:
        dispense_id = int(sys.argv[1])

        service = BillingService()
        result = service.generate_bill(dispense_id)

        print("\nPHARMACY BILL GENERATED")
        print("=======================")

        print("Bill ID:", result["bill_id"])
        print("Dispense ID:", result["dispense_id"])

        for index, line in enumerate(result["lines"], start=1):
            print(f"\nLINE {index}")
            print("Drug ID:", line["drug_id"])
            print("Quantity:", line["quantity"])
            print("MRP inclusive:", line["mrp_inclusive"])
            print("Discount rate:", line["discount_rate"], "%")
            print("Discount amount:", line["discount_amount"])
            print("Taxable value:", line["taxable_value"])
            print("GST:", line["gst_amount"])
            print("Line total:", line["line_total"])

        print("\nBILL SUMMARY")
        print("------------")
        print("Subtotal:", result["subtotal"])
        print("Discount:", result["discount_total"])
        print("GST:", result["gst_total"])
        print("Before rounding:", result["total_before_rounding"])
        print("Rounding:", result["rounding_adjustment"])
        print("Grand total:", result["grand_total"])

    except ValueError as error:
        print("Billing validation error:", error)

    except Exception as error:
        print("Billing failed:", error)


if __name__ == "__main__":
    main()
