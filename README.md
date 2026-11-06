# PS-061 – Pharmacy Inventory Management System

A Python and MySQL backend prototype for the PS-061 pharmacy inventory problem statement. The project is command-file driven in its intended design and does not require a graphical user interface.

## Technology

- Python 3.10+
- MySQL 8.0+
- `mysql-connector-python`
- `python-dotenv`
- `pytest`

## Project structure

```text
app/
  database/       MySQL schema and connection settings
  repositories/   Parameterized database queries
  services/       Pharmacy business logic
docs/             Design document, decision log and diagrams
tests/            Unit tests
run_*_demo.py     Small manual service demonstrations
```

## Local setup

1. Install Python 3.10+ and MySQL 8.0+.
2. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and enter your local MySQL connection settings. Never commit `.env`.
5. In MySQL Workbench, execute the SQL files in this order:
   - `app/database/schema.sql`
   - `app/database/dispensing_schema.sql`
   - `app/database/billing_schema.sql`
   - `app/database/compliance_schema.sql`
6. Confirm the configured database name is `pharmacy_inventory` (or change `DB_NAME` in your local `.env`).

> The schema scripts use `CREATE TABLE IF NOT EXISTS` and are for a fresh database setup. They do not automatically alter existing tables. Back up an existing database before applying any manual `ALTER TABLE` migration.

## Run tests

```powershell
python -m pytest -v
```

The current automated suite contains 73 unit tests covering:

- FEFO expiry-month handling, ordering and acute/chronic cutoffs;
- GST-inclusive billing arithmetic, discounts and bill rounding;
- prescription date, Schedule X quantity, rolling supply limits and refill validation;
- required-unit rounding, including exact-pack and one-unit-over-pack cases;
- OTC quantity limits, substitute selection, return eligibility, reorder rounding, expiry write-off valuation, supplier-return eligibility and recall timestamp checks.

These are unit tests. They do not constitute end-to-end MySQL integration tests for a complete dispensing transaction or register write.

## Demo runners

The Week 3 operational policy demo is safe and does not write to MySQL:

```powershell
python run_week3_rules_demo.py
```

See `docs/week3_demo_guide.md` for the demonstrated rule boundaries and limitations.


The `run_*_demo.py` files exercise individual service operations against the configured database. Some demos insert persistent records and use fixed demonstration IDs/batch numbers. Run them only against a disposable demo database or after checking the script inputs; do not repeatedly run them against a shared database.

Example:

```powershell
python run_drug_registration_demo.py
python run_batch_receiving_demo.py
python run_fefo_database_demo.py
```

The dispensing demo uses an existing prescription-line ID and customer ID; inspect the database first before running it. The billing demo requires an existing dispense ID:

```powershell
python run_billing_demo.py 1
```

## Current implementation status

Implemented in the current code snapshot:

- drug registration and substitution-group creation;
- supplier batch receiving and inventory receipt movements;
- FEFO selection with expiry-month handling and tie-breaking;
- prescription-line dispensing with partial-fill tracking;
- schedule validation helpers and H1/X register insert methods;
- GST-inclusive bill calculations, discount selection and whole-rupee bill rounding.

Implemented as database-independent decision helpers, but not yet connected as complete workflows in this code snapshot:

- OTC sale limit policy;
- generic substitute eligibility and cheapest-brand selection;
- customer-return eligibility and original-price refund calculation;
- reorder quantity calculation;
- supplier-return eligibility and recall timestamp comparison;
- near-expiry flag and expiry write-off valuation.

Still pending as complete workflows:

- command-file parsing and batch command execution (the official input format must be confirmed);
- connecting the above operational policies to MySQL transactions and reports;
- end-to-end MySQL integration tests for dispense, billing, returns, recalls and register transactions.

See `docs/design_document.md` for the complete BR-01 through BR-12 specification, `docs/week3_test_matrix.md` for rule-to-test mapping and implementation limitations, and `docs/decision_log.md` for unresolved assumptions. Do not present the unimplemented workflows as completed functionality.


## Week 3 operational database workflows

After the existing foundation, dispensing, billing and compliance schemas have
been applied, execute `app/database/operational_schema.sql` in MySQL Workbench.
This migration makes `prescription_id`, `patient_id` and
`prescription_line_id` nullable so OTC sale rows can share the bill/dispense
ledger, and creates customer-return, supplier-return, recall, write-off and
reorder tables. It is safe to rerun for the created tables; run the `ALTER TABLE`
statements once as part of the initial migration.

New workflows:

- `OTCSalesService().sell(customer_id, drug_id, quantity)` creates an OTC dispense
  transaction, applies the daily two-pack cap and deducts stock using eligible
  FEFO batches. It returns a `dispense_id`; create the bill using
  `BillingService().generate_bill(dispense_id)`.
- `DispensingService().dispense_prescription_line(...)` attempts same-group
  substitution only when no eligible prescribed-brand batch exists, unless the
  line is marked `NO_SUBSTITUTION`; it records both brands.
- `OperationalWorkflowService().process_customer_return(...)` validates and
  restores eligible stock to the original batch.
- `request_supplier_return(...)`, `complete_supplier_return(...)` and
  `cancel_supplier_return(...)` manage reservation and supplier return stock.
- `recall_batch(...)` freezes a batch and records the timestamp;
  `get_recall_violations(recall_id)` reports later dispenses.
- `run_end_of_day(business_date)` returns near-expiry alerts, writes off expired
  batches, defers batches with a pending supplier return, and persists reorder
  suggestions.

Example imports:

```python
from app.services.otc_service import OTCSalesService
from app.services.operational_workflow_service import OperationalWorkflowService

# Examples write to the configured MySQL database. Use a disposable database.
# otc = OTCSalesService().sell(customer_id=1, drug_id=1, quantity=10)
# ops = OperationalWorkflowService().run_end_of_day(date.today())
```

The official command-file sample/format was not included in the provided project
materials, so a parser/router has deliberately not been invented. These service
methods are callable from a command adapter once the required format is known.

**Integration warning:** Unit tests do not prove a live MySQL transaction. Apply
the migration to a backup/disposable database and exercise the new workflows
with synthetic records before using them on the existing demonstration data.

Verify the operational migration without modifying any data:

```powershell
python verify_operational_schema.py
```

The verifier checks for the operational tables and OTC-nullable columns; it is read-only.
