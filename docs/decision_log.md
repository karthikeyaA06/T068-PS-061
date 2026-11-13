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

9. Policy checks remain centralized in `app/services/operational_rules_service.py`; transactional MySQL workflows are implemented in `OTCSalesService`, `DispensingService` and `OperationalWorkflowService`. Live MySQL integration testing remains pending.
10. BR-01 cutoff interpretation in the current FEFO selector is strict: a chronic batch with exactly 30 calendar days remaining is excluded, and an acute batch with exactly 7 days remaining is excluded. This is covered by boundary tests and should be confirmed against the evaluator's expected output.
11. BR-05 substitute selection compares molecule, strength and dosage form, optionally enforcing matching `group_id` when the prescribed record has one. It filters to ACTIVE positive-stock candidates with MRP less than or equal to the prescribed MRP and chooses the lowest MRP, then brand name as a deterministic tie-break.
12. BR-08 return window is interpreted as an elapsed timestamp window of at most 7 × 24 hours. Exactly 60 days remaining is rejected because the rule requires more than 60 days.
13. BR-09 end-of-day workflow aggregates active, unexpired stock and subtracts quantities reserved for pending supplier returns before calculating reorder suggestions. A drug with any pending supplier return is excluded from that day's reorder list.
14. BR-10 a dispense is classified as post-recall only when its timestamp is strictly later than the recall timestamp. A transaction with the exact same timestamp is not classified as post-recall by this helper; event ordering at identical timestamps remains an integration-level concern.
15. The project brief specifies JSONL command files. The repository now implements the documented envelope in `docs/command_file_format.md`; exact compatibility with a faculty/evaluator sample remains unverified because that sample was not supplied.
16. OTC daily pack count is aggregated by customer and business date across Schedule NONE products. For each product, accumulated base units are rounded up to pack-equivalents once, then summed. New purchases are checked against the resulting customer-wide two-pack limit. This avoids letting repeat partial purchases evade the cap; confirm this interpretation against evaluator expectations.
17. Substitution is attempted only when no eligible batch exists for the prescribed brand, and the candidate must have the same substitution group and same schedule. The chosen brand's own pack size/full-pack flag is used for quantity rounding.
