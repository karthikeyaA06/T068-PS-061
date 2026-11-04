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