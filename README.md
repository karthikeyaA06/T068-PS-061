# T068-PS-061 – Pharmacy Inventory Management System

## 1\. Project Overview

The **Pharmacy Inventory Management System** is a Python-based application developed for problem statement PS-061. It is designed to support pharmacy inventory operations, medicine dispensing, billing, prescription validation and stock management.

The system includes business rules and workflows for:

* Medicine and supplier management
* Batch receiving and stock tracking
* FEFO (First Expiry, First Out) inventory selection
* Prescription validation and medicine dispensing
* Partial dispensing and pending quantities
* Billing and GST calculations
* Over-the-counter (OTC) sales
* Medicine substitution
* Customer returns and supplier returns
* Medicine recalls and compliance tracking
* Expiry management, stock write-offs and reorder suggestions
* End-of-day inventory reporting

The repository contains two separate execution paths:

1. **Official sample-pack execution:** Processes the supplied PS-061 sample data and generates evaluator-format CSV reports.
2. **MySQL-backed application:** Provides database-oriented services and a JSONL command interface for application workflows.

These execution paths are separate. The official sample-pack adapter processes its supplied commands in memory and does not persist those operations to MySQL.

\---

## 2\. Technology Stack

|Technology|Purpose|
|-|-|
|Python 3.10+|Application development|
|MySQL 8.0+|Persistent database storage|
|mysql-connector-python|Python–MySQL connectivity|
|python-dotenv|Environment configuration|
|pytest|Automated testing|
|Git and GitHub|Version control and project hosting|

\---

## 3\. Project Structure

```text
T068-PS-061/
│
├── app/
│   ├── database/
│   │   ├── schema.sql
│   │   ├── dispensing\_schema.sql
│   │   ├── billing\_schema.sql
│   │   ├── compliance\_schema.sql
│   │   └── operational\_schema.sql
│   │
│   ├── repositories/
│   │   └── Database query and persistence operations
│   │
│   ├── services/
│   │   └── Inventory, dispensing, billing,
│   │       prescription and operational services
│   │
│   └── commands/
│       └── JSONL command validation and dispatch
│
├── docs/
│   ├── design\_document.pdf
│   ├── design\_document.md
│   ├── decision\_log.md
│   ├── command\_file\_format.md
│   └── Additional project documentation
│
├── examples/
│   └── Illustrative JSONL command files
│
├── tests/
│   └── Automated unit and command-contract tests
│
├── T068-PS-061-sample-data/
│   └── Official sample-pack input files
│
├── official\_sample\_outputs/
│   └── Generated CSV reports (created when executed)
│
├── run\_official\_pack.py
├── validate\_official\_pack\_outputs.py
├── run\_commands.py
├── run\_mysql\_acceptance\_demo.py
├── prepare\_mysql\_test\_schema.py
├── verify\_operational\_schema.py
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

\---

## 4\. Quick Start – Official PS-061 Sample Pack

This is the primary execution path for processing the supplied official sample data.

### Requirements

* Python 3.10 or later
* Git
* The `T068-PS-061-sample-data` folder included in the repository

### Step 1: Clone the repository

```powershell
git clone https://github.com/karthikeyaA06/T068-PS-061.git

cd T068-PS-061
```

### Step 2: Create a virtual environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\\.venv\\Scripts\\Activate.ps1
```

### Step 3: Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### Step 4: Execute the official sample pack

```powershell
python run\_official\_pack.py --data-dir .\\T068-PS-061-sample-data --output-dir .\\official\_sample\_outputs
```

The program reads the sample-pack master data and processes the commands in sequence.

It generates six CSV output files.

### Step 5: Validate the generated outputs

```powershell
python validate\_official\_pack\_outputs.py --data-dir .\\T068-PS-061-sample-data --output-dir .\\official\_sample\_outputs
```

The validator checks output headers, required fields and the expected planted business scenarios.

### Step 6: Run the automated test suite

```powershell
python -m pytest -q
```

\---

## 5\. Generated Output Files

The official sample-pack execution generates the following CSV files:

|File|Description|
|-|-|
|`dispense\_lines.csv`|Medicine dispensing details, quantities and line statuses|
|`bills.csv`|Individual billing records|
|`bill\_totals.csv`|Bill-level totals and calculated amounts|
|`registers.csv`|Relevant prescription and controlled-medicine register records|
|`eod.csv`|End-of-day inventory activities and records|
|`violations.csv`|Recorded compliance and recall-related violations|

These files are generated inside the `official\_sample\_outputs/` directory.

**Note:** The generated output directory is ignored by Git. Run the official sample-pack command to recreate the output files locally.

\---

## 6\. Business Rules and Functionalities

### 6.1 Inventory Management

* Maintains medicine and batch information.
* Tracks received, available and reserved quantities.
* Supports stock receiving and inventory movements.
* Uses expiry information when determining stock eligibility.

### 6.2 FEFO Inventory Selection

The system uses the FEFO (First Expiry, First Out) principle.

Eligible medicine batches are selected according to expiry priority, with deterministic tie-breaking.

The implementation also considers expiry eligibility and stock reserved for supplier returns.

### 6.3 Prescription Validation

Prescription-related checks include:

* Prescription date validation
* Doctor registration validation
* Schedule H, H1 and X restrictions
* Prescription supply limits
* Rolling supply limits
* Refill eligibility

### 6.4 Medicine Dispensing

The dispensing workflow supports:

* Prescription-line processing
* Batch allocation
* Quantity and pack-size calculations
* Partial dispensing
* Pending quantities when stock is insufficient
* Medicine substitution under applicable conditions

### 6.5 Billing

The billing functionality includes:

* Bill and bill-line creation
* GST calculations
* Discount selection
* GST back-calculation
* Whole-rupee rounding

Financial calculations use decimal-based arithmetic.

### 6.6 OTC Sales

The OTC workflow includes:

* OTC eligibility validation
* Daily customer purchase limits
* Pack-equivalent calculations
* FEFO stock allocation
* Billing and inventory recording

### 6.7 Returns and Supplier Operations

The operational workflows include:

* Customer return eligibility checks
* Validation against original bill information
* Supplier-return requests
* Stock reservation for pending supplier returns
* Supplier-return completion and cancellation

### 6.8 Recall and Expiry Management

The system includes:

* Medicine recall recording
* Stock freezing for recalled batches
* Post-recall dispensing violation checks
* Near-expiry tracking
* Expired-stock write-off
* Reorder suggestions

\---

## 7\. Automated Testing and Validation

The project includes automated tests for business rules, service helpers, command contracts and schema-related checks.

### Run all tests

```powershell
python -m pytest -q
```

### Latest local verification

The latest completed local verification reported:

* **148 automated tests passed**
* **32/32 official sample-pack validation checks passed**
* **309 commands processed**
* **0 input or processing errors**
* **6 CSV output files generated**

The official sample-pack validator checks scenarios including:

* FEFO batch ordering and tie-breaking
* Duplicate prescription rejection
* Expiry eligibility
* Pack-size and quantity calculations
* Medicine substitution
* Near-expiry discounts
* Schedule X dispensing restrictions
* Partial dispensing
* Recall-related violations
* OTC purchase limits
* Doctor registration validation
* Refill restrictions
* Supplier-return stock reservation
* Expired-batch write-off

**Validation limitation:** The 32 checks verify the supplied planted scenarios and output structure. They do not establish a field-for-field match with faculty's hidden expected output.

\---

## 8\. MySQL Database Setup

The MySQL-backed application provides persistent database workflows separate from the official sample-pack adapter.

### Requirements

* MySQL Server 8.0+
* MySQL Workbench or another MySQL client
* Python dependencies installed

### Step 1: Configure environment variables

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Update the local database configuration in `.env` with your own MySQL settings.

**Important:** Never commit your actual `.env` file or database credentials to GitHub.

### Step 2: Create the database

Create or select a database named:

```sql
CREATE DATABASE pharmacy\_inventory;
```

### Step 3: Execute SQL schema files

Execute the SQL files in MySQL Workbench in this order:

1. `app/database/schema.sql`
2. `app/database/dispensing\_schema.sql`
3. `app/database/billing\_schema.sql`
4. `app/database/compliance\_schema.sql`
5. `app/database/operational\_schema.sql`

The operational migration includes `ALTER TABLE` statements. Back up an existing database before applying it, and check the current schema before applying migrations to an existing installation.

### Step 4: Verify the operational schema

```powershell
python verify\_operational\_schema.py
```

This script checks the presence of the required operational tables and columns.

\---

## 9\. JSONL Command Interface

The repository also provides a JSONL command-file interface through `run\_commands.py`.

Each non-empty line represents one JSON command.

Example:

```json
{"command\_id":"C001","command":"get\_fefo\_batches","parameters":{"drug\_id":1,"dispense\_date":"2026-11-06","days\_supply":10}}
```

Execute a JSONL command file using:

```powershell
python run\_commands.py commands.jsonl --output results.jsonl
```

Each input command produces a corresponding JSON result line.

Supported command names and parameter formats are documented in:

`docs/command\_file\_format.md`

**Important:** The JSONL command interface is different from the pipe-delimited command format used by the official sample pack. The official sample pack must be processed using `run\_official\_pack.py`.

\---

## 10\. MySQL Demonstrations

The repository contains scripts for demonstrating individual application workflows.

Examples include:

```powershell
python test\_db\_connection.py
python run\_drug\_registration\_demo.py
python run\_batch\_receiving\_demo.py
python run\_fefo\_database\_demo.py
python run\_dispensing\_demo.py
python run\_partial\_dispensing\_demo.py
```

The billing demonstration requires an existing dispense ID:

```powershell
python run\_billing\_demo.py <dispense\_id>
```

### Prepare a disposable MySQL test database

Generate the test database schema:

```powershell
python prepare\_mysql\_test\_schema.py
```

Execute the generated SQL file in MySQL Workbench to create the disposable `pharmacy\_inventory\_test` schema.

### Guarded MySQL acceptance demonstration

```powershell
$env:DB\_NAME = "pharmacy\_inventory\_test"

python run\_mysql\_acceptance\_demo.py

Remove-Item Env:DB\_NAME
```

The acceptance demonstration checks that the selected database is exactly `pharmacy\_inventory\_test` before running.

It creates synthetic records for testing and does not automatically delete them.

**Safety:** Run database-writing demonstrations only against a disposable test database. Do not run them against a shared or production database without reviewing their effects.

\---

## 11\. Project Documentation

Additional project documentation is available in the `docs/` directory.

| Document | Purpose |

|---|---|

| `design\_document.pdf` | Complete project design and technical documentation |

| `design\_document.md` | Markdown version of the design document |

| `decision\_log.md` | Architecture decisions, assumptions and open questions |

| `command\_file\_format.md` | JSONL command interface specification |

| `official\_sample\_data\_pack.md` | Documentation of the official sample data pack |

| `official\_sample\_pack\_audit.md` | Official sample-pack output audit details |

| `week3\_test\_matrix.md` | Business-rule and test mapping |

| `week3\_completion\_status.md` | Implementation status summary |

| `week3\_demo\_guide.md` | Project demonstration guidance |

| `mysql\_integration\_runbook.md` | MySQL integration and testing instructions |

| `week3\_submission\_report.md` | Week 3 submission report |

| `week3\_submission\_summary.md` | Week 3 submission summary |---

## 12\. Current Implementation and Validation Status

The repository contains business-rule helpers, MySQL-backed service workflows and a separate official sample-pack execution adapter.

The official sample-pack execution and its planted validation scenarios have passed the latest local checks.

The MySQL-backed workflows are implemented in the repository, but full end-to-end verification of every transaction path against a live MySQL database should be treated separately from the sample-pack results.

Similarly, compatibility with faculty's hidden field-for-field expected output has not been established by the 32 planted-scenario checks.

\---

## 13\. Project Demonstration Video

**Five-minute project demonstration:**

\[https://drive.google.com/file/d/16WSmI8F4_4KgYBnKaL4HPoNgfedu9Mf9/view?usp=drivesdk]

The demonstration covers:

1. Project introduction and problem statement
2. System architecture
3. Official sample-pack execution
4. Generated CSV output files
5. Automated testing and validation results
6. Project conclusion

\---

## 14\. Repository Information

**Project:** Pharmacy Inventory Management System

**Problem Statement ID:** PS-061

**Team ID:** T068

**GitHub Repository:**
https://github.com/karthikeyaA06/T068-PS-061

\---

## 15\. Conclusion

The Pharmacy Inventory Management System provides a structured approach to pharmacy inventory operations, medicine dispensing, prescription validation, billing and compliance-related workflows.

The project combines business-rule implementation, database-oriented application services, automated testing and official sample-pack processing to demonstrate the core requirements of the PS-061 problem statement.
