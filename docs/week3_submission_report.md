# PS-061 – Week 3 Submission Report

**Project:** Pharmacy Inventory with Batch Expiry, Schedule-H Control and Substitution  
**Team:** T068  
**Branch:** `main`  
**Submission date:** 6 November 2026

## 1. Week 3 objective

Week 3 focuses on implementing the business rules, covering the specified edge cases, and mapping automated tests to each business-rule identifier (BR-01 through BR-12).

## 2. Implementation completed in this source snapshot

- **Inventory and FEFO:** expiry-month end-date calculation, acute/chronic expiry cutoffs, FEFO ordering and deterministic tie-breaking.
- **Prescription dispensing:** required-unit calculation, pack rounding, partial-fill tracking, prescription/doctor/schedule validators and H1/X register insert methods.
- **Billing:** GST-inclusive MRP calculations, loyalty/near-expiry discount selection, GST back-calculation and whole-rupee rounding.
- **OTC:** service path for daily two-pack restriction, FEFO allocation and common dispense/bill ledger.
- **Substitution:** same-group substitute selection, price ceiling and recording of prescribed/dispensed brands.
- **Returns and stock operations:** customer-return validation and transaction method, supplier-return reservation/completion/cancellation, recall freezing and violation lookup, expiry write-off and reorder suggestion workflow.
- **Compliance:** rolling supply and refill policy validators for the relevant schedules.
- **Command layer:** JSONL line parser, allow-listed command dispatch, ISO date/time conversion, structured result/error JSONL and per-line error isolation.
- **Documentation:** design document, diagrams, decision log, business-rule test matrix, command-file format, completion status and demo guide.

## 3. Automated verification

The following checks passed in the isolated review environment:

| Check | Result |
|---|---|
| Python compilation (`compileall`) | Passed |
| Unit tests (`python -m pytest -q`) | **107 passed** |
| Safe in-memory Week 3 demo (`python run_week3_rules_demo.py`) | Completed successfully |

The review environment used a minimal MySQL connector import stub because it did not have a live MySQL server configured. Tests and the in-memory demo did not modify the user's database. Static schema-contract tests inspect SQL source text; they are not database integration tests. The user's earlier local run reported 86 passing tests; rerun the updated suite after copying the new command-layer files locally.

## 4. Rule-to-test traceability

See `docs/week3_test_matrix.md` for the BR-01 through BR-12 mapping and the edge-case matrix. The matrix distinguishes unit/helper tests from live database integration verification.

## 5. Outstanding acceptance work

The following items remain before claiming complete Week 3 acceptance:

1. Live MySQL integration tests for each transaction path, including success, error handling, rollback and stock/register consistency.
2. Verify actual H1/X register records created through dispensing.
3. Verify the operational migration against the final database schema and validate all foreign-key/column assumptions.
4. Compare the implemented JSONL command contract with the official faculty/evaluator sample, if supplied.
5. Run all commands against a disposable MySQL database and compare output with the official evaluator input/expected results, if supplied.

## 6. Submission statement

This submission demonstrates substantial Week 3 implementation progress, a 107-test passing automated suite, and a safe operational-policy demo. It does **not** claim complete end-to-end MySQL integration or compatibility with the official command-file sample. Those items are explicitly listed as remaining validation work.
