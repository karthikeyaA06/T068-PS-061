
# PS-061: Pharmacy Inventory Management System

**Document Version:** 0.2  
**Document Status:** Draft for Design Review  
**Problem Statement:** PS-061 – Pharmacy Inventory with Batch Expiry, Schedule-H Control and Substitution  
**Domain:** Healthcare – Pharmacy  
**Programming Language:** Python 3.10+  
**Database:** MySQL 8.0  
**Interface:** Command-file driven; no graphical user interface

---

## 1. Project Information

| Item | Details |
|---|---|
| Project ID | PS-061 |
| Project Title | Pharmacy Inventory with Batch Expiry, Schedule-H Control and Substitution |
| Domain | Healthcare – Pharmacy |
| Difficulty | High |
| Programming Language | Python 3.10+ |
| Database | MySQL 8.0 |
| Architecture | Layered Architecture |
| Input Interface | Command Files |
| Testing Framework | pytest |
| Version Control | Git and GitHub |

## 2. Introduction

The Pharmacy Inventory Management System is a command-file-driven backend application designed to manage hospital retail pharmacy operations.

The system manages drug registration, batch-wise inventory, supplier information, prescription validation, FEFO-based dispensing, Schedule H/H1/X controls, generic substitution, billing, customer and supplier returns, recalls, expiry write-offs, reorder calculations and reports.

The application receives commands from input files, processes them according to the project business rules, stores transactional data in MySQL, and produces the required dispense results, bills, registers and end-of-day reports.

The project does not require a graphical user interface.

## 3. Project Objectives

1. Maintain a drug master and batch-wise inventory with supplier and expiry information.
2. Receive stock and process eligible supplier returns.
3. Validate prescriptions and dispense medicines using FEFO batch selection.
4. Support partial fills while tracking pending quantities.
5. Enforce Schedule H, H1 and X restrictions, registers and dispensing limits.
6. Offer eligible generic substitutions and record substitution details.
7. Generate bills with per-line GST, discounts and bill-level rounding.
8. Process eligible customer returns and restore stock to the original batch.
9. Handle recalls, near-expiry alerts and expired-stock write-offs.
10. Generate reorder lists, stock reports and controlled-drug register reports.

## 4. Project Scope

### 4.1 In Scope

- Drug master registration and maintenance.
- Molecule-strength-form substitution group management.
- Supplier registration and batch receipt.
- Batch-wise stock tracking and inventory movements.
- Supplier returns and recall processing.
- Prescription creation and validation.
- FEFO dispensing and partial-fill handling.
- Schedule H/H1/X controls and registers.
- OTC pack limits.
- Generic substitution.
- GST-inclusive billing, discounts and rounding.
- Customer returns.
- Near-expiry alerts and expiry write-offs.
- Reorder calculations.
- Stock, register and end-of-day reports for requested dates.
- Command-file processing and structured output.

### 4.2 Out of Scope

- A graphical user interface.
- Online payments or payment-gateway integration, unless added as a separate requirement.
- Hospital-wide electronic health record integration, unless supplied as a separate requirement.
- Live integration with external doctor-registration or drug-regulatory databases.

## 5. Functional Requirements

The following functional requirements summarize the six core functional areas in the problem statement.

| ID | Functional Requirement |
|---|---|
| FR-01 | Register drugs with molecule, strength, form, brand, schedule, MRP, GST slab, pack size, minimum stock, full-pack flag and controlled-substance flag. Link brands to a molecule-strength-form substitution group. |
| FR-02 | Receive stock as batches with batch number, expiry month, quantity, purchase price and supplier. Process eligible supplier returns and recalled batches. |
| FR-03 | Accept prescriptions containing doctor registration number, date, patient and medicine lines. Validate and dispense using FEFO, including partial-fill and pending-line handling. |
| FR-04 | Enforce Schedule H/H1/X rules, maintain the H1 and X registers, enforce quantity and refill limits, and block over-dispensing. |
| FR-05 | Generate bills with per-line GST, discounts and rounding. Process customer returns according to the return policy. |
| FR-06 | Run end-of-day processing for near-expiry alerts, expired-stock write-offs and reorder lists. Produce stock and register reports for requested dates. |

## 6. Proposed Non-Functional Design Considerations

The following are proposed quality considerations for implementation. They supplement the functional requirements and do not replace the evaluator's acceptance criteria.

| ID | Design Consideration | Planned Approach |
|---|---|---|
| NFR-01 | Data Integrity | Use primary keys, foreign keys, unique constraints and database transactions where appropriate. |
| NFR-02 | Auditability | Record stock movements, dispense details, returns, recalls and write-offs with timestamps and references. |
| NFR-03 | Financial Accuracy | Use Python Decimal and MySQL DECIMAL; avoid binary floating-point for money. |
| NFR-04 | Repeatability | Process the same command data and business date deterministically, subject to specified ordering rules. |
| NFR-05 | Maintainability | Separate command parsing, validation, business services and database repositories. |
| NFR-06 | Testability | Map business-rule and edge-case tests to explicit BR and EC identifiers. |
| NFR-07 | Credential Protection | Store local database credentials in .env and exclude that file from version control. |

## 7. Glossary

| Term | Meaning |
|---|---|
| FEFO | First Expiry, First Out; select the eligible batch with the earliest expiry first. |
| MRP | Maximum Retail Price. |
| GST | Goods and Services Tax. |
| OTC | Over-the-Counter; a Schedule NONE sale that may be made without a prescription within the stated limit. |
| Schedule H | Drug schedule requiring a valid prescription under the project rules. |
| Schedule H1 | Drug schedule with additional register, refill and dispensing-limit controls under the project rules. |
| Schedule X | Drug schedule with stricter validity, quantity, refill, register and substitution controls under the project rules. |
| Substitution Group | Drugs sharing the same molecule, strength and form, used to identify eligible alternative brands. |
| Batch | A quantity of a drug received under one batch number and expiry month. |
| Partial Fill | Dispensing the available eligible quantity when valid stock is insufficient for the required quantity. |
| Pending Line | The undispensed quantity left after a partial fill, tracked for possible fulfilment within its validity period. |
| Recall | An event that freezes a batch and prohibits dispensing after the recall timestamp. |
| Write-off | Removal of expired stock from usable inventory, valued at purchase price under the project rule. |
| Rolling 90-Day Window | A moving period of 90 days used to calculate a patient's recent dispensed supply. |
| GST-Inclusive MRP | The MRP amount that already includes the applicable GST component. |

## 8. Business Rule Register

The following register records the twelve business rules supplied in PS-061. The implementation and tests must preserve these identifiers.

### BR-01: FEFO and Expiry Restrictions

1. Dispensing must follow First Expiry, First Out (FEFO).
2. A batch must not be selected if it falls within the applicable expiry restriction for the prescription: 30 days for chronic prescriptions (days supply greater than or equal to 30) or 7 days for acute prescriptions.
3. A batch remains valid through the last calendar day of its expiry month.
4. When two batches have the same expiry month, break the tie by earliest receipt date and then by batch number.
5. Only batches eligible for dispensing on the dispense date may be considered by the FEFO selector.

### BR-02: Quantity and Partial Fill

1. Required units are calculated as dose per day multiplied by number of days and rounded up to a whole unit.
2. If a drug is flagged as sold only in full packs, round the required quantity up to a whole number of packs.
3. A partial fill is allowed only when stock across valid eligible batches is less than the required quantity.
4. When a partial fill is allowed, dispense the available eligible stock and record the undispensed shortfall as a PENDING line.
5. A pending line created by a partial fill is valid for 7 days.
6. Dispensing must not exceed the remaining quantity required by the prescription line.

### BR-03: Schedule H, H1 and X Controls

1. Schedule H dispensing requires a valid doctor registration number and a prescription date within 30 days of the dispense date.
2. Schedule H1 has the additional requirement to record the patient and doctor in the H1 register.
3. Schedule H1 allows at most one refill within the prescription validity.
4. Schedule X prescriptions are valid for 7 days.
5. Schedule X prescriptions cannot be refilled.
6. Schedule X dispensing must not exceed 7 days' supply.
7. A Schedule X register entry must include the dispensed batch number.

### BR-04: OTC Restrictions

1. Schedule NONE drugs may be sold without a prescription.
2. Without a prescription, a customer may purchase up to 2 packs per day under the project limit.
3. A quantity beyond the stated OTC limit requires a prescription.
4. The daily count must be calculated consistently from the customer's sales records for the relevant business date.

### BR-05: Generic Substitution

1. If the prescribed brand is out of stock, the system may offer a substitute brand.
2. The substitute must belong to the same molecule-strength-form substitution group.
3. The substitute must have in-stock eligible quantity.
4. Select the cheapest eligible substitute whose MRP is less than or equal to the prescribed brand's MRP.
5. A substitute with MRP exactly equal to the prescribed MRP is eligible.
6. Schedule X drugs must never be substituted.
7. If the prescription contains NO_SUBSTITUTION, do not substitute; keep the line PENDING when the prescribed brand is unavailable.
8. Record both the prescribed brand and the dispensed substitute brand.

### BR-06: Pricing, GST and Discounts

1. Bill at GST-inclusive MRP.
2. For loyalty members, apply the following loyalty discount rates:
   - Schedule NONE: 10%.
   - Schedule H: 5%.
   - Schedule H1: 0%.
   - Schedule X: 0%.
3. For an eligible near-expiry batch, the near-expiry discount is 20%.
4. Loyalty and near-expiry discounts do not stack. Apply the higher applicable discount.
5. Apply the selected discount to the GST-inclusive MRP amount.
6. Back-calculate the GST component separately for each bill line using that drug's GST slab.
7. Round the final bill total to the nearest rupee and display the rounding adjustment.
8. The calculation must retain decimal precision until the defined line and bill rounding stages. The precise rounding mode and display precision must be documented and tested.

### BR-07: Near-Expiry and Expired-Stock Policy

1. Flag batches expiring within 90 days as NEAR_EXPIRY for the relevant business date.
2. Eligible sales from near-expiry batches receive a 20% discount under BR-06; this discount does not stack with loyalty discount.
3. Batches expiring within 30 days may only be sold for acute prescriptions, subject to the acute expiry restriction in BR-01.
4. Expired batches are written off on the first day of the month following their expiry month.
5. Value the write-off at the batch purchase price.
6. A near-expiry flag is date-dependent; it should be calculated for the business date rather than treated as a permanent batch lifecycle state.

### BR-08: Customer Returns

1. A customer return is allowed within 7 days of the original sale and requires the original bill.
2. Only unopened strips may be returned.
3. At the time of return, the original batch must have more than 60 days remaining before expiry. Exactly 60 days does not satisfy the more-than-60-days condition.
4. Schedule H1 and Schedule X items are never returnable.
5. Refund the billed price without an additional deduction.
6. Returned stock must be restored to its original batch, with an inventory movement recorded.

### BR-09: Reorder Calculation

1. At end of day, calculate the drug's total valid stock.
2. Generate a reorder when valid stock is less than the drug's minimum stock.
3. Calculate the base reorder quantity as:

   Reorder Quantity = 3 × Minimum Stock − Valid Stock

4. Round the reorder quantity up to a whole number of packs.
5. Exclude drugs that have a supplier return pending.
6. The definition of valid stock must exclude stock that is not available for sale, such as expired or frozen stock.

### BR-10: Supplier Returns and Recalls

1. A batch may be returned to the supplier if it has less than 90 days remaining to expiry and has never been dispensed from.
2. A recalled batch may also be returned to the supplier.
3. A recall command freezes the affected batch immediately at the recall timestamp.
4. Dispensing from a recalled batch after the recall timestamp is a violation and must be reported.
5. Record the recall reason and timestamp.
6. Timestamp comparison, not calendar-date comparison alone, is required when a recall and a dispense occur on the same day.

### BR-11: Dispensing Limits

1. A patient must not be dispensed more than 90 days' supply of any drug in a rolling 90-day window.
2. The Schedule H1 limit is 30 days' supply in the applicable rolling window.
3. If a request would exceed the applicable limit, reject it with REJECTED_LIMIT.
4. Calculate prior supply from recorded dispense transactions for the same patient and drug, using the applicable business dates and supply quantities.

### BR-12: Prescription Validity and Refills

1. A Schedule H prescription dated more than 30 days before dispensing must be rejected with REJECTED_EXPIRED_RX.
2. A refill may be dispensed only when at least 80% of the original days' supply has elapsed since the first dispense.
3. Apply the Schedule H1 one-refill limit and Schedule X no-refill rule in addition to the general refill-timing check.
4. Record validation and rejection outcomes with the specified status or reason.

## 9. Edge Case Register

The eight edge cases below come from the PS-061 problem statement. Each case must have an automated test and a documented expected outcome.

| ID | Edge Case | Required Handling / Expected Check |
|---|---|---|
| EC-01 | Two batches have the same expiry month. | Select by earliest receipt date; if tied, select by batch number. |
| EC-02 | A batch expires in exactly 30 days for a 30-day chronic prescription. | Test the exact BR-01 boundary. Confirm the interpretation against the expected output or evaluator clarification. |
| EC-03 | Required quantity is exactly one pack versus one unit above one pack. | Exactly one pack remains one pack; one unit above requires rounding to the next whole pack when the full-pack flag applies. |
| EC-04 | Substitute brand MRP exactly equals prescribed MRP. | The substitute is eligible because its MRP is less than or equal to the prescribed MRP. |
| EC-05 | Loyalty discount is 10% and near-expiry discount is 20% on the same line. | Apply 20% only; do not stack the discounts. |
| EC-06 | Return is attempted on day 7 at 23:59 with exactly 60 days remaining to expiry. | Check the 7-day limit using the sale and return timestamps. Reject the return because expiry remaining must be more than 60 days. |
| EC-07 | Schedule X prescription requests 8 days' supply. | Reject because Schedule X quantity must not exceed 7 days' supply. |
| EC-08 | A recall arrives after a partial dispense from the same batch on the same day. | Preserve a dispense that occurred before the recall timestamp; freeze the batch at recall time and report any dispense after that timestamp. |

## 10. Design Assumptions and Open Decisions

### 10.1 Proposed Design Assumptions

1. Inventory quantities are stored in a consistent base unit. Full-pack constraints are applied when calculating required and dispensed quantities.
2. Money is represented with Python Decimal and stored with MySQL DECIMAL columns.
3. A batch expiry month is stored in a form that allows the application to calculate the last calendar day of that month.
4. Stock changes are recorded as inventory movements with a reason, timestamp and source transaction reference.
5. Dispensing, stock reduction, dispense-line creation, billing records and register entries must use suitable database transactions so that a failed operation does not leave partial updates.
6. Near-expiry status is calculated relative to the business date.
7. Recall processing uses timestamps so that same-day event ordering is preserved.
8. The command parser will follow the actual sample command-file format supplied for the project; JSONL is not assumed until confirmed.

### 10.2 Open Decisions Requiring Confirmation

1. BR-01 exact boundary: Confirm whether a batch exactly 30 days from expiry is excluded for a 30-day chronic prescription, and apply the equivalent explicit rule to the 7-day acute boundary.
2. BR-02 full-pack partial fill: Confirm how partial fills are represented when a full-pack-only drug has insufficient stock to meet the next whole-pack requirement.
3. BR-04 OTC counting scope: Confirm from sample data or evaluator guidance whether the two-pack daily limit is counted across all Schedule NONE items or by a narrower product grouping. Do not silently add a per-drug rule.
4. BR-06 rounding: Confirm the required decimal precision for line GST and the rounding mode for the final nearest-rupee total.
5. BR-07 near-expiry boundary: Confirm whether exactly 90 days is included in the within-90-days flag.
6. BR-08 seven-day boundary: Confirm whether the return deadline is inclusive at the exact timestamp seven days after purchase.
7. BR-09 valid stock: Confirm the evaluator's treatment of stock allocated to a pending supplier return when calculating valid stock, in addition to excluding expired and frozen batches.
8. BR-11 rolling window: Confirm the exact inclusive/exclusive date boundary for the rolling 90-day calculation.
9. BR-12 refill timing: Confirm the day-count boundary for the 80% threshold, particularly when the calculation produces a fractional day.
10. Pending-line validity: The specification explicitly gives partial-fill pending lines a 7-day validity. It does not separately define the validity period for a NO_SUBSTITUTION pending line; confirm expected handling.
11. Time zone: Confirm the time zone used by the supplied command files and expected outputs for timestamp comparisons.

## 11. System Architecture

The application follows a layered architecture. Each layer has a separate responsibility so that command parsing, business rules and database access can be developed and tested independently.

### 11.1 Command Layer

- Reads the command files supplied to the application.
- Parses each command according to the confirmed input format.
- Validates command structure and sends the requested operation to the appropriate service.
- Produces structured command results and error responses.

### 11.2 Service Layer

- Implements the pharmacy business workflows.
- Coordinates drug registration, batch receiving, prescription processing, dispensing, billing, returns, recalls and end-of-day processing.
- Enforces business rules by calling the required validators and repositories.

### 11.3 Validation Layer

- Validates drug and batch data.
- Checks prescription dates, doctor registration details, schedule restrictions and refill eligibility.
- Checks stock, expiry, substitution eligibility and dispensing limits.
- Produces explicit validation outcomes and rejection reasons.

### 11.4 Repository Layer

- Encapsulates MySQL queries and persistence operations.
- Reads and writes drugs, suppliers, batches, prescriptions, dispense transactions, bills, returns, recalls, registers and reports.
- Uses parameterized SQL statements.

### 11.5 Database Layer

- Stores persistent pharmacy master data and transaction records.
- Enforces primary-key, foreign-key, unique and check constraints where supported and appropriate.
- Uses transactions for operations that must update multiple related records atomically.

### 11.6 High-Level Data Flow

```text
Command File
    |
    v
Command Processor
    |
    v
Input / Command Validation
    |
    v
Business Service Layer
    |
    +----> Prescription / Schedule Validation
    |
    +----> FEFO / Substitution / Inventory Logic
    |
    +----> Billing / Returns / End-of-Day Logic
    |
    v
Repository Layer
    |
    v
MySQL Database
    |
    v
Structured Results, Bills, Registers and Reports
```

## 12. Design Diagrams

The following diagrams are maintained as separate Markdown files under docs/diagrams/.

| Diagram | File | Purpose |
|---|---|---|
| UML Class Diagram | [class_diagram.md](diagrams/class_diagram.md) | Shows the main classes, their responsibilities and relationships. |
| State Diagrams | [state_diagrams.md](diagrams/state_diagrams.md) | Shows batch lifecycle and prescription-line lifecycle transitions. |
| Entity Relationship Diagram | [er_diagram.md](diagrams/er_diagram.md) | Shows the proposed database entities, keys and relationships. |

Note: These links require the corresponding diagram files to exist at the listed paths. The diagrams and database schema must be kept consistent as implementation decisions are finalized.

## 13. Testing Strategy

Testing will be performed at unit, integration and command-workflow levels.

### 13.1 Unit Testing

- Test individual validators and business services.
- Use deterministic dates and timestamps for expiry, prescription and return tests.
- Use Decimal test values for pricing and GST calculations.
- Test both successful outcomes and rejected operations.

### 13.2 Integration Testing

- Test Python-to-MySQL persistence.
- Test batch receipt and inventory movement updates.
- Test prescription-to-dispense workflows.
- Test stock reduction, billing and register creation within database transactions.
- Test customer returns and supplier returns against the original batch.

### 13.3 Business-Rule Test Traceability

| Business Rule | Minimum Test Coverage |
|---|---|
| BR-01 | FEFO ordering, tie-breaking, expiry-month last day, chronic and acute cutoffs. |
| BR-02 | Quantity rounding, full-pack rounding, sufficient stock, insufficient stock and pending shortfall. |
| BR-03 | Schedule H validity, H1 register and refill limit, X validity, X quantity and X register batch number. |
| BR-04 | OTC sale at the two-pack limit and sale above the limit without a prescription. |
| BR-05 | Same-group selection, cheapest eligible substitute, equal MRP, X prohibition and NO_SUBSTITUTION. |
| BR-06 | Loyalty rates, near-expiry discount selection, GST back-calculation and bill rounding. |
| BR-07 | 90-day near-expiry flag, 30-day sale restriction and first-day-of-following-month write-off. |
| BR-08 | Bill requirement, seven-day deadline, unopened condition, 60-day expiry condition, H1/X exclusion and original-batch restoration. |
| BR-09 | Below-minimum threshold, pack rounding and pending-supplier-return exclusion. |
| BR-10 | Expiry-based supplier return, never-dispensed condition, recall freeze and timestamp violation detection. |
| BR-11 | Rolling 90-day limit, H1 30-day limit and REJECTED_LIMIT. |
| BR-12 | Expired prescription rejection and 80% refill timing. |

### 13.4 Edge-Case Testing

Each case EC-01 through EC-08 in Section 9 must have at least one automated test. Tests must assert the exact dispense status, batch, quantity, substitution, bill values, register entries or rejection reason applicable to that case.

## 14. Conclusion

The proposed design defines the main scope, functional requirements, business rules, data relationships, state transitions and software layers for PS-061.

It provides the basis for the MySQL schema and Python implementation. The design will be refined against the sample command files and visible expected outputs, with each business rule traced to implementation and automated tests.
