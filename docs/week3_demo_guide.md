# Week 3 Demonstration Guide

## Safe operational-rule demo

Run from the project root:

```powershell
python run_week3_rules_demo.py
```

This script uses in-memory examples only. It does not connect to MySQL and does not modify database records.

It demonstrates:

- BR-04: the two-pack OTC threshold and rejection above the threshold;
- BR-05: selection of the cheapest eligible same-molecule/strength/form substitute;
- BR-07: the 90-day near-expiry boundary, validity through the expiry date and purchase-cost write-off valuation;
- BR-08: rejection at exactly 60 days remaining and refund at the original billed amount when eligible;
- BR-09: reorder quantity rounded to full packs and exclusion while a supplier return is pending;
- BR-10: supplier-return eligibility and timestamp-sensitive recall checks.

## Important limitation

The demo proves the behavior of database-independent policy helpers only. It does not prove that these rules are wired into MySQL transactions, stock restoration/freezing, audit movements, end-of-day reports or command-file processing. Those workflows must be described as pending until implemented and tested.
