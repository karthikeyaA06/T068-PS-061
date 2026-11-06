# PS-061 – Pharmacy Inventory Management System

A Python and MySQL backend prototype for the PS-061 pharmacy inventory problem statement. The backend includes a JSON Lines (JSONL) command runner. Each non-empty input line is one command object; see `docs/command_file_format.md`. The command contract is a documented project interface and must still be compared with the faculty/evaluator sample if one is provided.

## Technology

- Python 3.10+
- MySQL 8.0+
- `mysql-connector-python`
- `python-dotenv`
- `pytest`

## Project structure

```text
app/
  database/       MySQL connection and SQL schema/migration files
  repositories/   Parameterized database queries
  services/       Inventory, dispensing, billing and operational workflows
  commands/       JSONL validation and command dispatch
docs/             Design document, decision log, diagrams and Week 3 evidence
examples/         Read-only illustrative JSONL command file
tests/            Automated unit tests
run_*_demo.py     Manual service demonstrations
run_commands.py   JSONL command-file runner
verify_operational_schema.py  Read-only operational-schema check
```

## Local setup

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

4. Copy `.env.example` to `.env` and enter your local MySQL connection settings. Keep the real `.env` local; never commit or submit it. The repository should contain only `.env.example` with placeholder values.
5. Create/select the `pharmacy_inventory` database, then execute the SQL files in MySQL Workbench in this order:
   - `app/database/schema.sql`
   - `app/database/dispensing_schema.sql`
   - `app/database/billing_schema.sql`
   - `app/database/compliance_schema.sql`
   - `app/database/operational_schema.sql`

   The operational migration contains `ALTER TABLE` statements as well as table creation. Back up an existing database before applying it, and apply the migration only once unless its statements have been made idempotent. Do not apply a fresh-install schema over an existing database without checking the current schema first.

6. Confirm that the database name in `.env` is `pharmacy_inventory`, or change `DB_NAME` to match your local database.

## Run automated tests

From the repository root, with the virtual environment activated:

```powershell
python -m pytest -v
```

**Updated package automated-test count: 107.** This count was reproduced in the isolated review environment; rerun the suite locally after copying the updated package. The test suite covers:

- FEFO expiry-month conversion, eligibility cutoffs, ordering, tie-breaking and reserved supplier-return stock;
- required dispensing quantity, pack rounding and partial-fill calculations;
- prescription date, doctor, Schedule H/H1/X, rolling supply and refill validation;
- GST-inclusive billing, discount selection, GST back-calculation and whole-rupee rounding;
- OTC limits, substitute eligibility, customer-return conditions, reorder calculations, write-off valuation, supplier-return eligibility and recall timestamps.

The tests include unit/helper, command-contract and static schema-contract checks. They do **not** establish that every transaction works end-to-end against a live MySQL database.

## Demonstrations

### Safe Week 3 policy demonstration

This demonstration uses in-memory sample values and does not write to MySQL:

```powershell
python run_week3_rules_demo.py
```

Expected final message:

```text
Week 3 operational helper demo completed successfully.
```

### Database-backed demonstrations

The following scripts connect to the configured MySQL database and may create or modify persistent records:

```powershell
python test_db_connection.py
python run_drug_registration_demo.py
python run_batch_receiving_demo.py
python run_fefo_database_demo.py
python run_dispensing_demo.py
python run_partial_dispensing_demo.py
```

Run database-writing demos only against a disposable/demo database or after reviewing their fixed IDs, quantities and batch numbers. Do not repeatedly run them against a shared database. The billing demo requires an existing dispense ID:

```powershell
python run_billing_demo.py <dispense_id>
```

### Operational schema verification

The following script is read-only and checks for the operational tables and OTC-related nullable columns:

```powershell
python verify_operational_schema.py
```

The earlier terminal log confirmed the policy demo and 86 tests. The updated package adds command-contract, OTC aggregation-boundary and schema-contract tests; the isolated review run for this updated snapshot reports 107 passing tests. A previous attempt to run `verify_operational_schema.py` was mistyped, so run it separately to verify the current database schema.


## JSONL command-file interface

The project brief identifies JSONL command files. This repository provides a documented command envelope:

```json
{"command_id":"C001","command":"get_fefo_batches","parameters":{"drug_id":1,"dispense_date":"2026-11-06","days_supply":10}}
```

Run a UTF-8 JSONL file with:

```powershell
python run_commands.py commands.jsonl --output results.jsonl
```

Each non-empty input line produces one JSON result line. A failed command is reported for that line and does not stop subsequent lines. Supported command names and parameter formats are listed in `docs/command_file_format.md`. This is the project's documented JSONL interface; confirm the exact envelope and operation names against any official faculty/evaluator sample before relying on evaluator compatibility. Commands that create or modify records should be run only against a disposable/demo database.

## Current implementation status

The code snapshot contains both **business-rule/policy helpers** and **database workflow methods**. These are different levels of implementation and should not be described as equivalent.

### Core application workflows present in code

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

### Policy helpers and unit coverage

`OperationalRulesService` contains independently testable decision helpers for OTC eligibility, substitution selection, near-expiry/expired-date checks, write-off valuation, return eligibility, reorder quantities, supplier-return eligibility and recall timestamp comparisons. `PrescriptionComplianceService` contains prescription, rolling-limit and refill validators.

### Remaining validation and acceptance work

The following are **not yet claimed as fully accepted**:

1. Live MySQL integration testing for all transaction paths, including commit/rollback behavior, stock consistency, duplicate requests and register consistency.
2. End-to-end verification that actual H1/X dispensing creates the expected register rows in the configured database.
3. Live transaction verification of OTC sales, substitution, customer returns, supplier returns, recall freezes/violations, write-offs and reorder suggestions using synthetic data in a disposable database.
4. Compare the implemented JSONL command envelope and operation names in `docs/command_file_format.md` against the official faculty/evaluator sample, if supplied. The parser is implemented for the documented project contract but evaluator compatibility is not yet verified.
5. Execution of the official evaluator input and comparison against its expected output.

See `docs/design_document.md` for BR-01 through BR-12, `docs/week3_test_matrix.md` for rule-to-test mapping and integration status, `docs/week3_completion_status.md` for the completion summary, `docs/week3_demo_guide.md` for the demo, and `docs/decision_log.md` for assumptions and unresolved decisions.

## Week 3 submission statement

The updated Week 3 snapshot has **107 automated tests passing in the isolated review environment** and a successful safe operational-policy demo. Core service methods for the listed inventory, dispensing, billing and operational workflows are present. Full live-MySQL end-to-end verification and comparison with the official command-file evaluator sample remain outstanding; they are not represented as complete in this README.
