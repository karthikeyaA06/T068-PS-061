# Week 3 – Business Rule and Test Matrix

**Project:** PS-061 – Pharmacy Inventory with Batch Expiry, Schedule-H Control and Substitution  
**Test command:** `python -m pytest -v`  
**Updated package test count:** 139 automated tests

This matrix distinguishes business-rule/unit logic, command-contract checks, static schema checks and live database integration. Passing unit tests alone does not prove a complete MySQL transaction.

| Rule | Implementation in this snapshot | Automated coverage | Live integration status |
|---|---|---|---|
| BR-01 FEFO and expiry | `FEFOSelector` converts expiry month to month-end, applies acute/chronic cutoff and deterministic tie-breaks | `tests/test_fefo.py` | FEFO is used by dispensing; live MySQL transaction test pending |
| BR-02 Quantity and partial fill | `DispensingService.calculate_required_units` and FEFO allocation track fulfilled and pending quantities | `tests/test_dispensing.py` | Allocation code present; live MySQL partial-fill test pending |
| BR-03 H/H1/X controls | `PrescriptionComplianceService` validators are called from dispensing; repository inserts H1/X register rows | `tests/test_compliance.py`, `tests/test_prescription_service.py` | Actual H1/X register insert and rollback need live DB test |
| BR-04 OTC restrictions | `OTCSalesService.sell` aggregates same-customer/business-day pack-equivalents across Schedule NONE products, enforces the two-pack cap and allocates eligible FEFO stock | `tests/test_operational_rules.py`, `tests/test_otc_service.py` | Live MySQL OTC sale/stock/bill test pending |
| BR-05 Generic substitution | Dispensing queries same-group/same-schedule candidates, applies price ceiling/availability, records both brands and respects X/NO_SUBSTITUTION | `tests/test_operational_rules.py` | Live MySQL substitution and mixed-pack edge test pending |
| BR-06 Billing, GST and discounts | `BillingService` calculates inclusive MRP, discounts, per-line GST and final rupee rounding with `Decimal` | `tests/test_billing.py` | Calculations tested; live bill persistence/duplicate-bill test pending |
| BR-07 Near-expiry and write-off | End-of-day service reports near-expiry batches and writes off expired stock at purchase cost | `tests/test_fefo.py`, `tests/test_operational_rules.py` | Live MySQL EOD/write-off test pending |
| BR-08 Customer returns | Operational workflow validates bill/date/condition/schedule/expiry, caps cumulative returns and restores original batch | `tests/test_operational_rules.py` | Live MySQL return/refund/rollback test pending |
| BR-09 Reorder | EOD service aggregates active, unexpired, unreserved stock and stores pack-rounded suggestions | `tests/test_operational_rules.py` | Live MySQL aggregation/report test pending |
| BR-10 Supplier returns and recalls | Workflow reserves/completes/cancels returns, freezes recalled batch and queries post-recall dispensing | `tests/test_operational_rules.py` | Live MySQL lock/rollback/timestamp test pending |
| BR-11 Rolling dispensing limits | Repository reads days supply across the substitution group; compliance service enforces 90-day/H1 limit | `tests/test_compliance.py` | Live SQL window/concurrency test pending |
| BR-12 Prescription validity/refills | Prescription date, doctor registration, Schedule X 7-day/no-refill, H1 one-refill and 80%-elapsed checks | `tests/test_compliance.py` | Live MySQL refill workflow test pending |

## Edge-case mapping

| Edge case | Automated test(s) |
|---|---|
| Same expiry month: receipt date then batch number | `test_same_expiry_tie_broken_by_receipt_date`, `test_same_expiry_and_receipt_tied_by_batch_number` |
| Chronic batch exactly 30 days away | `test_chronic_batch_exactly_30_days_is_excluded` |
| Exact pack vs one unit above | `test_required_units_exactly_one_pack_stays_one_pack`, `test_required_units_one_above_pack_rounds_to_next_pack` |
| Substitute MRP equals prescribed MRP | `test_br05_equal_mrp_is_allowed` |
| Near-expiry discount overrides loyalty | `test_near_expiry_overrides_loyalty`, `test_near_expiry_discount_does_not_stack` |
| Return at seven-day boundary with exactly 60 days to expiry | `test_br08_day_7_2359_with_60_days_expiry_rejected` |
| Schedule X eight-day supply | `test_schedule_x_eight_days_rejected` |
| Recall after same-day partial dispense | `test_br10_preserve_pre_recall_dispense_and_flag_post_recall` |
| Partial and cross-product OTC purchases aggregated before applying two-pack cap | `test_otc_daily_cap_rounds_combined_partial_sales_only_once`, `test_otc_daily_cap_rejects_combined_units_above_two_packs`, `test_otc_daily_pack_equivalents_aggregate_across_distinct_products`, `test_otc_pack_equivalents_reject_third_pack_across_products` |

## BR-11 rolling-window boundary

The dispensing service queries the prior 30 calendar days for Schedule H1 and the prior 90 calendar days for the general rolling limit. The current unit tests verify the schedule-to-window selection. A live database test is still required to prove that the SQL query and transaction enforce the same window with real dispense history.

## Additional test layers

- `tests/test_master_data_service.py` validates master-data input rules. `tests/test_prescription_service.py` validates quantity calculations, transactional prescription creation using a fake connection, decimal dose persistence, Schedule X eight-day rejection and expired Schedule H prescription rejection.
- `tests/test_command_processor.py` validates JSONL parsing, explicit command allow-list, typed date/time parameters, Decimal/date serialization, structured errors and continuation after a malformed command line.
- `tests/test_schema_contract.py` statically checks expected table/column declarations across SQL scripts. It does not connect to MySQL.
- `verify_operational_schema.py` is a read-only live-database schema verifier. Run it from the project root after configuring `.env` and applying the migrations.

## Remaining acceptance work

1. Run `python verify_operational_schema.py` against the configured MySQL database and retain the result.
2. Run integration tests for each transaction against a backup/disposable database, including success, rejection, rollback, stock balances, inventory movements, return records and H1/X registers.
3. Compare `docs/command_file_format.md` with any official faculty/evaluator JSONL sample and adjust field names/command names if required.
4. Run the official evaluator input and compare structured output with expected results.

The updated package has 139 automated tests passing in the isolated review environment. These tests are not a substitute for the live MySQL and evaluator checks listed above.
