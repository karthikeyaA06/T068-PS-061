# MySQL Integration Runbook

This runbook is for a **disposable test database**, not the database containing the team's existing demo records.

## 1. Prepare a separate database

1. Back up the current `pharmacy_inventory` database.
2. From the project root, run:

   ```powershell
   python prepare_mysql_test_schema.py
   ```

3. Open the generated `pharmacy_inventory_test_schema.sql` in MySQL Workbench and execute the full script. It creates/selects `pharmacy_inventory_test` and combines the migrations in the required order: foundation, dispensing, billing, compliance, operational.
4. Do not drop or recreate the team's normal `pharmacy_inventory` database for this test.

## 2. Point the application at the test database

Keep `.env` private. Temporarily set the database name in the local `.env` to `pharmacy_inventory_test`, run the tests below, then restore the normal database name. Alternatively, set a PowerShell environment variable for the current terminal session:

```powershell
$env:DB_NAME = "pharmacy_inventory_test"
```

The process inherits this value and the connection module uses it in preference to the `.env` value.

## 3. Verify schema (read-only)

```powershell
python verify_operational_schema.py
```

Expected output starts with `Operational schema verification PASSED` and reports seven operational tables and verifies the three nullable OTC columns. It does not validate every base-table column.

## 4. Create synthetic master data through the command runner

Create a JSONL file containing one command per line, using unique test labels:

```json
{"command_id":"T001","command":"register_supplier","parameters":{"supplier_name":"PS061 Integration Supplier"}}
{"command_id":"T002","command":"register_customer","parameters":{"customer_name":"PS061 Integration Customer","loyalty_member":true}}
{"command_id":"T003","command":"register_doctor","parameters":{"registration_number":"PS061-TEST-REG-001","doctor_name":"PS061 Integration Doctor"}}
{"command_id":"T004","command":"register_patient","parameters":{"patient_name":"PS061 Integration Patient"}}
{"command_id":"T005","command":"register_drug","parameters":{"molecule":"Integration Molecule","strength":"10 mg","dosage_form":"Tablet","brand_name":"PS061-TEST-BRAND-A","schedule":"H1","mrp":"50.00","gst_rate":"5.00","pack_size":10,"min_stock":10,"sells_full_packs":false,"controlled_substance":false}}
```

Run it:

```powershell
python run_commands.py integration_master_data.jsonl --output integration_master_data_results.jsonl
```

Inspect the result file and record the returned IDs. Do not assume IDs are 1.

## 5. Add a batch and prescription

Use the IDs returned by Step 4 in a second JSONL file. Choose an expiry month safely beyond the prescription eligibility cutoffs. Use a unique batch number.

Example shape (replace the IDs):

```json
{"command_id":"T101","command":"receive_batch","parameters":{"drug_id":1,"supplier_id":1,"batch_number":"PS061-INT-H1-001","expiry_month":"2027-12","quantity":100,"purchase_price":"15.00"}}
{"command_id":"T102","command":"create_prescription","parameters":{"doctor_id":1,"patient_id":1,"prescription_date":"2026-11-14","lines":[{"drug_id":1,"dose_per_day":"1.0","days_supply":5,"no_substitution":false}]}}
```

Run the file, inspect the IDs returned by `create_prescription`, and use the returned `prescription_line_id` for the next command.

## 6. Exercise dispensing, H1 register and billing

Use the actual IDs from the previous output:

```json
{"command_id":"T201","command":"dispense_prescription_line","parameters":{"prescription_line_id":1,"customer_id":1,"dispense_date":"2026-11-14"}}
```

Take the returned `dispense_id` and generate the bill:

```json
{"command_id":"T202","command":"generate_bill","parameters":{"dispense_id":1}}
```

Confirm the H1 register and bill records in Workbench:

```sql
SELECT * FROM h1_register_entries ORDER BY h1_entry_id DESC LIMIT 5;
SELECT * FROM bills ORDER BY bill_id DESC LIMIT 5;
SELECT * FROM bill_lines ORDER BY bill_line_id DESC LIMIT 5;
```

## 7. Test rejection and stock integrity

Use new synthetic prescriptions/lines for each test. Check:

- Schedule X with eight days' supply is rejected before stock deduction.
- A Schedule X dispense writes the X register with batch number.
- An H1 refill before 80% elapsed is rejected and does not change stock.
- An OTC Schedule NONE purchase above the daily cap is rejected and does not change stock.
- A `NO_SUBSTITUTION` line remains pending when the prescribed brand has no eligible stock.
- A customer return restores only the allowed quantity to the original batch and records the return movement.
- A pending supplier return reduces saleable stock; cancel releases the reservation; completion reduces physical stock.
- Recall freezes the batch and the violation query identifies only dispenses after the recall timestamp.
- End-of-day writes off expired batches once and excludes drugs with any pending supplier return from reorder suggestions.

After every rejected command, compare `batches.available_quantity`, `inventory_movements`, prescription-line status and register/return tables before and after. Stock must not change on a rejected/rolled-back transaction.

## 8. Restore normal settings

```powershell
Remove-Item Env:DB_NAME -ErrorAction SilentlyContinue
```

Confirm `.env` again points to the normal database. Do not copy any test database credentials into GitHub. Keep all synthetic records confined to `pharmacy_inventory_test`.

## Limitations

This runbook describes manual live-MySQL acceptance checks. The isolated review environment cannot connect to the user's MySQL server, so successful transaction behavior must be established by running these checks locally and recording the results. The JSONL field/operation contract must also be compared with any official faculty sample.
## 9. Run the guarded acceptance smoke test

After the schema and synthetic setup are complete, run the project acceptance script against the disposable database only. It checks a focused path through H1 dispensing/register/billing, Schedule X register, partial fill, same-group substitution, OTC sale cap, customer return, supplier return reservation/cancel/completion, recall freeze, expired write-off, reorder suggestion and H1/X reports. It creates uniquely named synthetic records and leaves them in the test database for inspection.

```powershell
$env:DB_NAME = "pharmacy_inventory_test"
python run_mysql_acceptance_demo.py
Remove-Item Env:DB_NAME
```

The script verifies the actual database name before making any changes and exits without writes unless it is exactly `pharmacy_inventory_test`. A successful run is a focused live-MySQL smoke test, not proof of every concurrency, rollback or evaluator edge case. Retain the terminal output and inspect the generated rows before the final demonstration.

