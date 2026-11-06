# PS-061 – Design Decision Log

| ID | Decision | Reason | Status |
|---|---|---|---|
| D-01 | Python 3.10+ | Required project language | Accepted |
| D-02 | MySQL database | Persistent inventory storage | Accepted |
| D-03 | Layered architecture | Separation of responsibilities | Proposed |
| D-04 | Decimal for money | Accurate financial calculations | Accepted |
| D-05 | FEFO batch selection | Earliest eligible expiry first | Accepted |
| D-06 | Base-unit stock tracking | Accurate quantity calculations | Proposed |
| D-07 | pytest for testing | Automated business-rule testing | Accepted |
| D-08 | Git and GitHub | Version control and collaboration | Accepted |

## Open Questions

1. Confirm the refill calculation for Schedule H1.
2. Confirm date and timestamp handling for recalls.
3. Confirm rounding precision for per-line GST.
4. Confirm pending-line expiry and fulfilment behaviour.
## Week 3 implementation notes

9. Operational rule helpers for OTC limits, substitution choice, customer-return eligibility, reorder quantity, near-expiry/write-off and supplier-return/recall checks are implemented as database-independent policy functions in `app/services/operational_rules_service.py`. They are covered by unit tests but are not yet called from end-to-end MySQL workflows.
10. BR-01 cutoff interpretation in the current FEFO selector is strict: a chronic batch with exactly 30 calendar days remaining is excluded, and an acute batch with exactly 7 days remaining is excluded. This is covered by boundary tests and should be confirmed against the evaluator's expected output.
11. BR-05 substitute selection compares molecule, strength and dosage form, optionally enforcing matching `group_id` when the prescribed record has one. It filters to ACTIVE positive-stock candidates with MRP less than or equal to the prescribed MRP and chooses the lowest MRP, then brand name as a deterministic tie-break.
12. BR-08 return window is interpreted as an elapsed timestamp window of at most 7 × 24 hours. Exactly 60 days remaining is rejected because the rule requires more than 60 days.
13. BR-09 reorder logic expects the caller to supply already-computed valid stock (excluding expired, frozen, depleted or otherwise unavailable inventory). The helper calculates only the reorder quantity and pack rounding.
14. BR-10 a dispense is classified as post-recall only when its timestamp is strictly later than the recall timestamp. A transaction with the exact same timestamp is not classified as post-recall by this helper; event ordering at identical timestamps remains an integration-level concern.
15. The official command-file format was not present in the supplied project materials. A parser was not invented; implement it once the required command-file sample/schema is available.
