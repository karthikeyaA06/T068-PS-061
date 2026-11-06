# PS-061 – Week 3 Submission Summary

## Work completed in this snapshot

- Implemented FEFO selection with expiry-month end-date calculation, chronic/acute cutoff rules, and receipt-date/batch-number tie-breaking.
- Implemented required quantity calculation, including full-pack rounding, and the existing prescription-line partial-dispense workflow.
- Implemented prescription validation helpers for Schedule H/H1/X, rolling supply limits, H1 refill count, Schedule X no-refill and 80% refill timing.
- Implemented GST-inclusive bill-line calculation, loyalty/near-expiry discount selection, GST back-calculation and whole-rupee bill rounding.
- Added database-independent operational policy helpers for OTC limits, substitute selection, customer-return eligibility, reorder quantity, near-expiry/write-off calculations, supplier-return eligibility and recall timestamp comparisons.
- Added a BR-to-test matrix and a Week 3 decision/limitation record.
- Added `run_week3_rules_demo.py`, a safe in-memory demonstration for BR-04, BR-05 and BR-07 through BR-10; it performs no database writes.

## Unit test result

The updated package's unit suite contains 86 tests. In the isolated review environment, all 86 passed. The review environment used a minimal MySQL connector import stub because it did not have the connector package installed; the tests exercised calculation/policy logic and did not connect to MySQL.

Run the authoritative local test command in the project's activated virtual environment:

```powershell
python -m pytest -v
```

## Work that is not complete

- The official command-file parser/router is not implemented; the exact input command-file format must first be confirmed.
- The official command-file parser/router is not implemented because the official input file format was not included in the supplied materials.
- Live MySQL end-to-end testing is still required for the new OTC, substitution, customer/supplier return, recall, write-off and reorder transactions, plus H1/X register writes and rollback.
- End-to-end acceptance testing against the evaluator's exact command file and expected outputs remains pending.

## Submission wording

The current Week 3 snapshot contains implemented service workflows for the identified business rules and 86 passing automated unit tests. It should not be described as fully accepted until the operational schema migration is applied and live MySQL integration tests plus the evaluator-format command-file run have been completed.
