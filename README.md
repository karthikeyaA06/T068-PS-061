# PS-061 – Pharmacy Inventory Management System

A Python and MySQL backend prototype for the PS-061 pharmacy inventory problem statement. The intended interface is command-file driven; no graphical user interface is required by the current design.

## Technology

- Python 3.10+
- MySQL 8.0+
- `mysql-connector-python`
- `python-dotenv`
- `pytest`

## Project Structure

```text
PharmacyInventory/
│
├── app/
│   ├── database/
│   │   ├── connection.py
│   │   ├── schema.sql
│   │   ├── dispensing_schema.sql
│   │   ├── billing_schema.sql
│   │   ├── compliance_schema.sql
│   │   └── operational_schema.sql
│   │
│   ├── repositories/
│   │   ├── drug_repository.py
│   │   ├── batch_repository.py
│   │   ├── dispensing_repository.py
│   │   └── billing_repository.py
│   │
│   └── services/
│       ├── drug_service.py
│       ├── batch_service.py
│       ├── fefo_service.py
│       ├── inventory_service.py
│       ├── dispensing_service.py
│       ├── billing_service.py
│       ├── compliance_service.py
│       ├── operational_rules_service.py
│       ├── otc_service.py
│       └── operational_workflow_service.py
│
├── docs/
│   ├── design_document.md
│   ├── decision_log.md
│   ├── week3_test_matrix.md
│   ├── week3_completion_status.md
│   ├── week3_demo_guide.md
│   └── diagrams/
│
├── tests/
│   ├── test_fefo.py
│   ├── test_billing.py
│   ├── test_compliance.py
│   ├── test_dispensing.py
│   ├── test_operational_rules.py
│   └── test_otc_service.py
│
├── run_drug_registration_demo.py
├── run_batch_receiving_demo.py
├── run_fefo_database_demo.py
├── run_dispensing_demo.py
├── run_partial_dispensing_demo.py
├── run_billing_demo.py
├── run_week3_rules_demo.py
├── test_db_connection.py
├── verify_operational_schema.py
│
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

## Local Setup

1. Install Python 3.10+ and MySQL 8.0+.

2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and enter your local MySQL connection settings.

Keep the real `.env` file private. Never commit or submit it. Only `.env.example` with placeholder values should be included in GitHub.

5. Create or select the `pharmacy_inventory` database, then execute the SQL files in MySQL Workbench in this order:

- `app/database/schema.sql`
- `app/database/dispensing_schema.sql`
- `app/database/billing_schema.sql`
- `app/database/compliance_schema.sql`
- `app/database/operational_schema.sql`

The operational migration contains `ALTER TABLE` statements as well as table creation. Back up an existing database before applying it, and apply the migration only once unless its statements have been made idempotent.

Do not apply a fresh-install schema over an existing database without checking the current schema first.

6. Confirm that the database name in `.env` is `pharmacy_inventory`, or change `DB_NAME` to match your local database.

## Run Automated Tests

From the repository root, with the virtual environment activated:

```powershell
python -m pytest -v
```

**Latest reported local result for this Week 3 snapshot: 86 tests passed.**

The test suite covers:

- FEFO expiry-month conversion, eligibility cutoffs, ordering, tie-breaking and reserved supplier-return stock.
- Required dispensing quantity, pack rounding and partial-fill calculations.
- Prescription date, doctor, Schedule H/H1/X, rolling supply and refill validation.
- GST-inclusive billing, discount selection, GST back-calculation and whole-rupee rounding.
- OTC limits, substitute eligibility, customer-return conditions, reorder calculations, write-off valuation, supplier-return eligibility and recall timestamps.

These 86 tests are unit/helper tests. They do not establish that every transaction works end-to-end against a live MySQL database.

## Demonstrations

### Safe Week 3 Policy Demonstration

This demonstration uses in-memory sample values and does not write to MySQL:

```powershell
python run_week3_rules_demo.py
```

Expected final message:

```text
Week 3 operational helper demo completed successfully.
```

### Database-Backed Demonstrations

The following scripts connect to the configured MySQL database and may create or modify persistent records:

```powershell
python test_db_connection.py
python run_drug_registration_demo.py
python run_batch_receiving_demo.py
python run_fefo_database_demo.py
python run_dispensing_demo.py
python run_partial_dispensing_demo.py
```

Run database-writing demos only against a disposable/demo database or after reviewing their fixed IDs, quantities and batch numbers.

Do not repeatedly run them against a shared database.

The billing demo requires an existing dispense ID:

```powershell
python run_billing_demo.py <dispense_id>
```

### Operational Schema Verification

The following script is read-only and checks for the operational tables and OTC-related nullable columns:

```powershell
python verify_operational_schema.py
```

The Week 3 terminal log supplied for this report confirms that the policy demo completed and the 86-test suite passed. It also shows that a prior attempt to run `verify_operational_schema.py` was mistyped, so the script's successful execution is not claimed here.

The operational tables were separately checked in MySQL Workbench.

## Current Implementation Status

The code snapshot contains both **business-rule/policy helpers** and **database workflow methods**. These are different levels of implementation and should not be described as equivalent.

### Core Application Workflows Present in Code

- Drug registration and substitution-group creation (`DrugService`).
- Supplier batch receiving and inventory receipt movements (`BatchService`).
- FEFO eligibility, expiry-month handling, ordering and tie-breaking (`FEFOSelector` and `InventoryService`).
- Prescription-line dispensing, batch allocation, partial-fill tracking and inventory movements (`DispensingService`).
- Schedule validation calls and H1/X register insertion methods in the dispensing transaction (`PrescriptionComplianceService` and `DispensingRepository`).
- GST-inclusive billing calculations and persisted bill/bill-line creation (`BillingService`).
- OTC sale transaction path with daily quantity restriction and FEFO stock allocation (`OTCSalesService`).
- Same-group substitute selection in prescription dispensing when the prescribed brand has no eligible stock; prescribed and dispensed brands are retained (`DispensingService`).
- Customer-return transaction that validates the original bill line and restores eligible quantity to its original batch (`OperationalWorkflowService.process_customer_return`).
- Supplier-return request, reservation, completion and cancellation (`OperationalWorkflowService`).
- Recall recording/freezing and lookup of post-recall dispensing violations (`OperationalWorkflowService`).
- End-of-day near-expiry output, expired-batch write-off and persisted reorder suggestions (`OperationalWorkflowService.run_end_of_day`).

### Policy Helpers and Unit Coverage

`OperationalRulesService` contains independently testable decision helpers for:

- OTC eligibility.
- Substitution selection.
- Near-expiry and expired-date checks.
- Write-off valuation.
- Customer-return eligibility.
- Reorder quantities.
- Supplier-return eligibility.
- Recall timestamp comparisons.

`PrescriptionComplianceService` contains prescription, rolling-limit and refill validators.

### Remaining Validation and Acceptance Work

The following are not yet claimed as fully accepted:

1. Live MySQL integration testing for all transaction paths, including commit/rollback behavior, stock consistency, duplicate requests and register consistency.
2. End-to-end verification that actual H1/X dispensing creates the expected register rows in the configured database.
3. Live transaction verification of OTC sales, substitution, customer returns, supplier returns, recall freezes/violations, write-offs and reorder suggestions using synthetic data in a disposable database.
4. The command-file parser/router and batch command execution. The official command-file sample and exact input format were not included in the materials reviewed; the parser must be implemented against that specification rather than an invented format.
5. Execution of the official evaluator input and comparison against its expected output.

See:

- `docs/design_document.md` for BR-01 through BR-12.
- `docs/week3_test_matrix.md` for rule-to-test mapping and integration status.
- `docs/week3_completion_status.md` for the completion summary.
- `docs/week3_demo_guide.md` for the demonstration.
- `docs/decision_log.md` for assumptions and unresolved decisions.

## Week 3 Submission Statement

The Week 3 snapshot has a reported local result of **86 passing automated tests** and a successful safe operational-policy demo.

Core service methods for the listed inventory, dispensing, billing and operational workflows are present.

Full live-MySQL end-to-end verification and command-file evaluator acceptance remain outstanding; they are not represented as complete in this README.