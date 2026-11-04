
# PS-061 – Entity Relationship Diagram
## Pharmacy Inventory Management System

```mermaid
erDiagram

    SUBSTITUTION_GROUP {
        int group_id PK
        string molecule
        string strength
        string form
    }

    DRUG {
        int drug_id PK
        int group_id FK
        string brand_name
        string schedule
        decimal mrp
        decimal gst_rate
        int pack_size
        int min_stock
        boolean sells_full_packs
        boolean controlled_substance
    }

    SUPPLIER {
        int supplier_id PK
        string name
        string phone
        string address
    }

    BATCH {
        int batch_id PK
        int drug_id FK
        int supplier_id FK
        string batch_number
        date expiry_month_start
        datetime received_at
        int received_quantity
        int available_quantity
        decimal purchase_price
        string status
    }

    DOCTOR {
        int doctor_id PK
        string registration_number UK
        string name
        boolean is_active
    }

    PATIENT {
        int patient_id PK
        string patient_name
        string contact
    }

    CUSTOMER {
        int customer_id PK
        string customer_name
        string contact
        boolean loyalty_member
    }

    PRESCRIPTION {
        int prescription_id PK
        int doctor_id FK
        int patient_id FK
        date prescription_date
    }

    PRESCRIPTION_LINE {
        int prescription_line_id PK
        int prescription_id FK
        int drug_id FK
        decimal dose_per_day
        int days_supply
        decimal prescribed_mrp
        boolean no_substitution
    }

    DISPENSE {
        int dispense_id PK
        int prescription_id FK
        int customer_id FK
        int patient_id FK
        datetime dispensed_at
        string status
    }

    DISPENSE_LINE {
        int dispense_line_id PK
        int dispense_id FK
        int prescription_line_id FK
        int drug_id FK
        int batch_id FK
        int quantity
        decimal days_supply_dispensed
        boolean is_substituted
        datetime dispensed_at
    }

    BILL {
        int bill_id PK
        int dispense_id FK
        decimal subtotal
        decimal discount_total
        decimal gst_total
        decimal rounding_adjustment
        decimal grand_total
        datetime bill_date
    }

    BILL_LINE {
        int bill_line_id PK
        int bill_id FK
        int dispense_line_id FK
        int quantity
        decimal mrp_inclusive
        decimal discount_rate
        decimal discount_amount
        decimal gst_rate
        decimal taxable_value
        decimal gst_amount
        decimal line_total
    }

    CUSTOMER_RETURN {
        int return_id PK
        int bill_id FK
        datetime return_date
        string status
    }

    CUSTOMER_RETURN_LINE {
        int return_line_id PK
        int return_id FK
        int bill_line_id FK
        int dispense_line_id FK
        int quantity
        boolean unopened
        decimal refund_amount
    }

    SUPPLIER_RETURN {
        int supplier_return_id PK
        int supplier_id FK
        datetime requested_at
        string status
    }

    SUPPLIER_RETURN_LINE {
        int return_line_id PK
        int supplier_return_id FK
        int batch_id FK
        int quantity
        string reason
    }

    RECALL {
        int recall_id PK
        int batch_id FK
        datetime recalled_at
        string reason
    }

    INVENTORY_MOVEMENT {
        int movement_id PK
        int batch_id FK
        string movement_type
        int quantity_delta
        datetime movement_at
        string reference_type
        int reference_id
    }

    H1_REGISTER_ENTRY {
        int entry_id PK
        int dispense_line_id FK
        string patient_name
        string doctor_registration_number
        datetime dispense_date
        int quantity
    }

    X_REGISTER_ENTRY {
        int entry_id PK
        int dispense_line_id FK
        string patient_name
        string doctor_registration_number
        string batch_number
        datetime dispense_date
        int quantity
    }

    END_OF_DAY_RUN {
        int run_id PK
        date run_date
        datetime executed_at
    }

    EXPIRY_WRITE_OFF {
        int writeoff_id PK
        int run_id FK
        int batch_id FK
        int quantity
        decimal purchase_price
        decimal total_writeoff
    }

    REORDER_RECOMMENDATION {
        int recommendation_id PK
        int run_id FK
        int drug_id FK
        int valid_stock
        int minimum_stock
        int reorder_quantity
    }

    SUBSTITUTION_GROUP ||--o{ DRUG : contains
    DRUG ||--o{ BATCH : has
    SUPPLIER ||--o{ BATCH : supplies

    DOCTOR ||--o{ PRESCRIPTION : writes
    PATIENT ||--o{ PRESCRIPTION : owns
    PRESCRIPTION ||--|{ PRESCRIPTION_LINE : contains
    DRUG ||--o{ PRESCRIPTION_LINE : prescribed

    PRESCRIPTION o|--o{ DISPENSE : authorizes
    CUSTOMER ||--o{ DISPENSE : purchases
    PATIENT o|--o{ DISPENSE : receives

    DISPENSE ||--|{ DISPENSE_LINE : contains
    PRESCRIPTION_LINE o|--o{ DISPENSE_LINE : fulfilled_by
    DRUG ||--o{ DISPENSE_LINE : dispensed_drug
    BATCH ||--o{ DISPENSE_LINE : picked_from

    DISPENSE ||--o| BILL : generates
    BILL ||--|{ BILL_LINE : contains
    DISPENSE_LINE ||--o| BILL_LINE : billed_as

    BILL ||--o{ CUSTOMER_RETURN : original_bill
    CUSTOMER_RETURN ||--|{ CUSTOMER_RETURN_LINE : contains
    BILL_LINE ||--o{ CUSTOMER_RETURN_LINE : returned_from
    DISPENSE_LINE ||--o{ CUSTOMER_RETURN_LINE : original_dispense

    SUPPLIER ||--o{ SUPPLIER_RETURN : receives
    SUPPLIER_RETURN ||--|{ SUPPLIER_RETURN_LINE : contains
    BATCH ||--o{ SUPPLIER_RETURN_LINE : returned_batch

    BATCH ||--o{ RECALL : has
    BATCH ||--o{ INVENTORY_MOVEMENT : records

    DISPENSE_LINE ||--o| H1_REGISTER_ENTRY : creates
    DISPENSE_LINE ||--o| X_REGISTER_ENTRY : creates

    END_OF_DAY_RUN ||--o{ EXPIRY_WRITE_OFF : produces
    BATCH ||--o{ EXPIRY_WRITE_OFF : written_off

    END_OF_DAY_RUN ||--o{ REORDER_RECOMMENDATION : produces
    DRUG ||--o{ REORDER_RECOMMENDATION : recommended_for
```

## Important Database Design Notes

1. Molecule, strength and form are maintained in the substitution group.
2. Each drug belongs to one substitution group.
3. Each drug can have multiple batches.
4. Each batch belongs to a supplier.
5. A prescription can contain multiple prescription lines.
6. A dispense line records the actual drug and batch dispensed.
7. Billing stores GST and discount calculations separately.
8. Customer returns link back to the original bill and dispense.
9. Schedule H1 and X register entries are maintained separately.
10. Inventory movements provide an audit trail of stock changes.
