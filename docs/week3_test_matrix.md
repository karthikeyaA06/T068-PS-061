# Week 3 – Business Rule and Test Matrix

**Project:** PS-061 – Pharmacy Inventory with Batch Expiry, Schedule-H Control and Substitution  
**Test command:** `python -m pytest -v`  
**Current unit-test count in this package:** 73

This matrix distinguishes pure service/unit coverage from database workflow verification. A passing unit test does not, by itself, prove that the corresponding MySQL transaction or command-file path is integrated.

| Rule | Implemented logic in this snapshot | Automated test coverage | Integration status |
|---|---|---|---|
| BR-01 FEFO and expiry | `FEFOSelector`: expiry-month end date, acute/chronic cutoffs, FEFO sorting and tie-breakers | `tests/test_fefo.py` | FEFO selection is used by dispensing; database transaction still needs a live integration test |
| BR-02 Quantity and partial fill | Required-unit rounding and partial-fill allocation in `DispensingService` | `tests/test_dispensing.py` | Allocation path exists; live MySQL partial-fill verification pending |
| BR-03 H/H1/X controls | `PrescriptionComplianceService`; dispensing calls validators and repository exposes H1/X register inserts | `tests/test_compliance.py` | Register inserts and rollback behavior need live MySQL verification |
| BR-04 OTC restrictions | `OperationalRulesService.validate_otc_sale` | `tests/test_operational_rules.py` | Daily prior-sales lookup and OTC transaction path not yet connected |
| BR-05 Generic substitution | `OperationalRulesService.choose_substitute` selects cheapest in-stock same molecule/strength/form substitute at MRP <= prescribed MRP; blocks X and NO_SUBSTITUTION | `tests/test_operational_rules.py` | Pure decision helper only; not yet called by `DispensingService` or persisted to dispense lines |
| BR-06 Billing, GST and discounts | `BillingService` uses Decimal, inclusive-MRP discount, GST back-calculation and final rupee rounding | `tests/test_billing.py` | Calculation coverage present; full MySQL bill transaction needs live test |
| BR-07 Near-expiry and write-off | Near-expiry date flag, expiry-date test and purchase-price write-off valuation helpers | `tests/test_fefo.py`, `tests/test_operational_rules.py` | End-of-day batch write-off/update transaction not connected |
| BR-08 Customer returns | Return eligibility, seven-day timestamp window, unopened status, H1/X exclusion, >60-day expiry and original-price refund calculation | `tests/test_operational_rules.py` | Return/batch-restoration transaction and inventory movement not connected |
| BR-09 Reorder calculation | Three-times-minimum target, pack rounding and pending-supplier-return exclusion | `tests/test_operational_rules.py` | Valid-stock aggregation and reorder report not connected |
| BR-10 Supplier returns and recalls | Supplier-return eligibility and timestamp-based post-recall violation helper | `tests/test_operational_rules.py` | Recall storage/freeze and supplier-return stock transaction not connected |
| BR-11 Rolling dispensing limits | 90-day limit and H1 30-day limit validator | `tests/test_compliance.py` | SQL history aggregation is present in dispensing repository; live boundary/concurrency tests pending |
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
2. BR-04, BR-05, BR-07 to BR-10 now have pure decision helpers and unit tests, but their full database workflows are not connected.
3. A live MySQL integration test is still required for dispense + stock movement + H1/X register inserts + rollback as one transaction.
4. The Week 3 unit suite is not the same as a complete acceptance test of all PS-061 workflows.
