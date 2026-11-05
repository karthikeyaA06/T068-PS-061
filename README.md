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

The current automated suite contains 46 unit tests covering:

- FEFO expiry-month handling, ordering and acute/chronic cutoffs;
- GST-inclusive billing arithmetic, discounts and bill rounding;
- prescription date, Schedule X quantity, rolling supply limits and refill validation;
- required-unit rounding, including exact-pack and one-unit-over-pack cases.

These are unit tests. They do not constitute end-to-end MySQL integration tests for a complete dispensing transaction or register write.

## Demo runners

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

Not yet implemented as complete workflows in this code snapshot:

- command-file parsing and batch command execution;
- OTC sale limit enforcement;
- selecting and dispensing generic substitute brands;
- customer returns;
- supplier returns and timestamped recall processing;
- end-of-day expiry write-offs and reorder recommendations;
- full MySQL integration tests for dispense, billing and register transactions.

See `docs/design_document.md` for the complete BR-01 through BR-12 specification and `docs/decision_log.md` for unresolved assumptions. Do not present the unimplemented workflows as completed functionality.
