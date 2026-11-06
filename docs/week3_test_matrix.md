# Week 3 – Business Rule and Test Matrix

**Project:** PS-061 – Pharmacy Inventory with Batch Expiry, Schedule-H Control and Substitution  
**Test command:** `python -m pytest -v`  
**Current unit-test count in this package:** 86

This matrix distinguishes pure service/unit coverage from database workflow verification. A passing unit test does not, by itself, prove that the corresponding MySQL transaction or command-file path is integrated.

| Rule | Implemented logic in this snapshot | Automated test coverage | Integration status |
|---|---|---|---|
| BR-01 FEFO and expiry | `FEFOSelector`: expiry-month end date, acute/chronic cutoffs, FEFO sorting and tie-breakers | `tests/test_fefo.py` | FEFO selection is used by dispensing; database transaction still needs a live integration test |
| BR-02 Quantity and partial fill | Required-unit rounding and partial-fill allocation in `DispensingService` | `tests/test_dispensing.py` | Allocation path exists; live MySQL partial-fill verification pending |
| BR-03 H/H1/X controls | `PrescriptionComplianceService`; dispensing calls validators and writes H1/X register rows within the dispense transaction | `tests/test_compliance.py` | Register inserts and rollback behavior need live MySQL verification |
| BR-04 OTC restrictions | `OTCSalesService.sell` enforces daily two-pack counting and executes stock/dispense transaction; pure policy helper retained | `tests/test_operational_rules.py`, `tests/test_otc_service.py` | Live MySQL transaction and cross-item cap need verification |
| BR-05 Generic substitution | `DispensingService` queries same-group/same-schedule brands and records prescribed/dispensed brands; policy chooses cheapest eligible substitute; blocks X and NO_SUBSTITUTION | `tests/test_operational_rules.py` | Live MySQL dispensing/substitution and pack-size boundary need verification |
| BR-06 Billing, GST and discounts | `BillingService` uses Decimal, inclusive-MRP discount, GST back-calculation and final rupee rounding | `tests/test_billing.py` | Calculation coverage present; full MySQL bill transaction needs live test |
| BR-07 Near-expiry and write-off | `OperationalWorkflowService.run_end_of_day` returns date-based near-expiry flags and writes off expired stock at purchase price | `tests/test_fefo.py`, `tests/test_operational_rules.py` | Live MySQL end-of-day run and deferred supplier-return case need verification |
| BR-08 Customer returns | `OperationalWorkflowService.process_customer_return` locks original bill line, validates eligibility, limits previously returned quantity, restores original batch and records movement/refund | `tests/test_operational_rules.py` | Live MySQL return and partial-return transaction need verification |
| BR-09 Reorder calculation | `OperationalWorkflowService.run_end_of_day` aggregates active unexpired stock less pending supplier returns and persists pack-rounded suggestions | `tests/test_operational_rules.py` | Live MySQL EOD aggregation and report verification pending |
| BR-10 Supplier returns and recalls | `OperationalWorkflowService` reserves/completes/cancels supplier returns, freezes recalled batches, timestamps recalls and queries post-recall violations | `tests/test_operational_rules.py` | Live MySQL lock/rollback and violation query need verification |
| BR-11 Rolling dispensing limits | 90-day and H1 30-day validators; repository counts prior dispense days across the same substitution group | `tests/test_compliance.py` | Live SQL boundary/concurrency tests pending |
| BR-12 Prescription validity and refills | Prescription age, Schedule X 7-day limit/no-refill, H1 one-refill and 80% elapsed validators | `tests/test_compliance.py` | Validator calls are in dispensing service; end-to-end refill tests pending |

## Edge-case mapping

| Edge case | Test(s) |
|---|---|
| EC-01 Same expiry month: receipt date then batch number | `test_same_expiry_tie_broken_by_receipt_date`, `test_same_expiry_and_receipt_tied_by_batch_number` |
| EC-02 Exactly 30 days for chronic | `test_chronic_batch_exactly_30_days_is_excluded` |
| EC-03 Exact pack vs one unit over | `test_required_units_exactly_one_pack_stays_one_pack`, `test_required_units_one_above_pack_rounds_to_next_pack` |
| EC-04 Substitute MRP equals prescribed MRP | `test_br05_equal_mrp_is_allowed` |
| EC-05 Near-expiry discount overrides loyalty | `test_near_expiry_overrides_loyalty`, `test_near_expiry_discount_does_not_stack` |
| EC-06 Return with exactly 60 days to expiry | `test_br08_day_7_2359_with_60_days_expiry_rejected` |
| EC-07 Schedule X eight-day supply | `test_schedule_x_eight_days_rejected` |
| EC-08 Recall timestamp after same-day partial dispense | `test_br10_preserve_pre_recall_dispense_and_flag_post_recall` |

## Week 3 limitations to disclose

1. The command-file parser/router described in the architecture is not implemented in this snapshot. The input file format must be confirmed against the official sample before implementing it.
2. BR-04, BR-05, BR-07 to BR-10 now have database workflow service methods and policy tests; live MySQL execution tests are still pending.
3. Live MySQL integration tests are still required for OTC sales, dispensing/substitution, stock movement, customer/supplier returns, recall freezing, end-of-day write-offs/reorders, H1/X register inserts and rollback.
4. The Week 3 unit suite is not the same as a complete acceptance test of all PS-061 workflows.
