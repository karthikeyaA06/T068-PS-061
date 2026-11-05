from app.services.drug_service import DrugService


def main():
    service = DrugService()

    try:
        result = service.register_drug(
            molecule="Paracetamol",
            strength="500 mg",
            dosage_form="Tablet",
            brand_name="PS061-DEMO-PARA-500",
            schedule="NONE",
            mrp="25.00",
            gst_rate="5.00",
            pack_size=10,
            min_stock=20,
            sells_full_packs=False,
            controlled_substance=False
        )

        print("\nDRUG REGISTRATION SUCCESSFUL")
        print("Drug ID:", result["drug_id"])
        print("Group ID:", result["group_id"])
        print("Brand:", result["brand_name"])
        print("Status:", result["status"])

    except ValueError as error:
        print("Registration failed:", error)

    except Exception as error:
        print("Database operation failed:", error)


if __name__ == "__main__":
    main()