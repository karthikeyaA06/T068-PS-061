# T068-PS-061 Official Sample Pack – Output Audit

**Audit basis:** The supplied `T068-PS-061-sample-data` pack and its README/edge-case map.
**Runner:** `run_official_pack.py` (in-memory sample-pack adapter; does not write to MySQL).
**Result:** 32/32 output-contract and planted-scenario checks passed.

## Reproduction

From the project root:

```powershell
python run_official_pack.py --data-dir .\T068-PS-061-sample-data --output-dir .\official_sample_outputs
python validate_official_pack_outputs.py --data-dir .\T068-PS-061-sample-data --output-dir .\official_sample_outputs
```

The validator checks the six required CSV headers and important planted scenarios. It does not compare against a faculty golden output; the sample-pack README states that expected outputs are not supplied and that a separate hidden set is used at evaluation.

## Run summary

- Commands processed: **309**
- Input/processing errors: **0**
- Expected business rejections: **12**
- `dispense_lines.csv`: **657** rows
- `bills.csv`: **642** rows
- `bill_totals.csv`: **219** rows
- `registers.csv`: **352** rows
- `eod.csv`: **1,209** rows
- `violations.csv`: **13** rows
- Output headers: all six match the supplied output contract.

## Planted scenarios checked

| Scenario | Observed result |
|---|---|
| EC-01 – same-expiry FEFO tie-break | RX-0030 picked AMX4471 (30 units), then AMX4468 (15 units); the duplicate command was rejected. |
| EC-02 – exactly 30 days for chronic supply | RX-0106 excluded the 2026-10 expiry batch and selected the later eligible batch. |
| EC-03 – exact pack / one unit over | RX-0060 dispensed exactly 100 units. RX-0061 calculated 200 full-pack units but was rejected by BR-11's 90-day supply limit. See open interpretation below. |
| EC-04 – equal-MRP substitution | RX-0075 selected DRG-035 (Feblin) at the same MRP as DRG-034 and recorded the prescribed drug in `substitute_of`. |
| EC-05 – loyalty vs near-expiry discount | RX-0121 used `NEAR_EXPIRY` and a 20% discount (Rs 10.40); loyalty was not stacked. |
| EC-06 – day 7 at 23:59, exactly 60 expiry days | The return was rejected with `INSUFFICIENT_EXPIRY_REMAINING`; it appears in `violations.csv`, not `dispense_lines.csv`. |
| EC-07 – Schedule X 8 days / exactly 7 days | RX-0133 was rejected with `X_SUPPLY_LIMIT`. RX-0140 was dispensed for 7 days and appears in the X register with a batch number. |
| EC-08 – late-arriving recall after partial dispense | RX-0141 dispensed 20 of 30 units, left 10 pending, and the later-arriving recall flagged the 11:20 dispense against the 10:45 effective timestamp. |
| Extra – Schedule X must not substitute | RX-0173 remained `PENDING` with no substituted drug. |
| Extra – third OTC pack | OTC-0902 was rejected with `OTC_LIMIT`. |
| Extra – expired Schedule H prescription | RX-0007 was rejected with `REJECTED_EXPIRED_RX`. |
| Extra – invalid doctor | RX-0093 was rejected with `INVALID_DOCTOR`. |
| Extra – H1 refill sequence | RX-0013: day-7 refill rejected, day-8 refill accepted and registered, later refill rejected with `REFILL_LIMIT`. |
| Extra – H1 rolling limit | PAT-0069's 20-day and 15-day Clonazepam supplies in the same group were counted together; RX-0067 was rejected at 35 days in the rolling 90-day period. |
| Extra – supplier return / reorder | BAT-0004 supplier return was accepted as pending; the Primamet reorder was suppressed on 2026-10-06. |
| Extra – expiry write-off | BAT-0001 was written off on 2026-10-01 for 45 units at purchase cost Rs 82.08. |

## Items to clarify with the faculty

1. **RX-0061 rule interaction:** The sample pack's EC-03 text uses a 101-day request to demonstrate one-unit-over full-pack rounding (101 units rounds to 200 units). BR-11 limits a non-H1 prescription to 90 days in a rolling 90-day window. The current result calculates 200 units but rejects the dispense as `REJECTED_LIMIT`. This is the conservative interpretation of the stated limit; ask whether the evaluator expects BR-11 rejection or intends EC-03 to override that cap.
2. **`PRINT_STOCK` output:** The command reference says `PRINT_STOCK|date` means stock by batch at end of that date, but the supplied output-file section defines only six CSV files and does not define a stock output file or columns. The current adapter accepts the command and applies no separate stock export. Ask whether stock should be emitted to console or in an additional file, and what its exact schema should be.
3. **Register snapshots:** `registers.csv` is specified as H1/X entries per `PRINT_REGISTER`. The runner therefore emits a cumulative snapshot for each print command, so earlier register entries repeat. The prescribed register schema has no snapshot/as-of date column. Confirm that repeated snapshot rows are intended.
4. **Successful return coverage:** The supplied command pack contains one customer return scenario (EC-06), and that return is expected to be rejected. A successful customer-return/refund path is therefore not demonstrated by this official pack, even though it has a separate MySQL smoke-test scenario in the project.

## Important evaluation limitation

These results establish that the runner processes the supplied sample pack without parsing/runtime errors and that the planted scenarios listed above produce the documented outcomes. They do **not** establish field-for-field agreement with the hidden evaluator set. Retain the decision log and seek clarification for the three output/rule-format ambiguities above before freezing the evaluator submission.
