# Official T068-PS-061 Sample Data Pack

## Input pack

The team-specific pack is the folder `T068-PS-061-sample-data` that you extracted from `Capstone_Sample_Data_Packs_Atria`. It can remain anywhere inside the repository; pass its actual folder path through `--data-dir`.

It contains the seven CSV master/transaction files plus `commands.txt` and the supplier-provided `README.md`:

| File | Data rows / lines |
|---|---:|
| `drugs.csv` | 120 |
| `suppliers.csv` | 5 |
| `batches.csv` | 323 |
| `doctors.csv` | 25 |
| `patients.csv` | 130 |
| `prescriptions.csv` | 200 |
| `prescription_lines.csv` | 594 |
| `commands.txt` | 309 commands |

The pack's IDs are string IDs (`DRG-...`, `BAT-...`, `PAT-...`, `RX-...`). They are not the integer primary keys in the development MySQL schema.

## Important command-format distinction

The application's general-purpose `run_commands.py` accepts JSONL objects. The official pack's `commands.txt` is a different, pipe-delimited format:

`COMMAND_NAME|arg1|arg2|...`

Do **not** pass the official `commands.txt` file to `run_commands.py`. Use the official-pack adapter:

```powershell
python run_official_pack.py --data-dir "<path-to-T068-PS-061-sample-data>" --output-dir "official_sample_outputs"
```

The adapter processes non-comment, non-empty command lines in file order and writes these six CSVs with the exact headers in the pack README:

- `dispense_lines.csv`
- `bills.csv`
- `bill_totals.csv`
- `registers.csv`
- `eod.csv`
- `violations.csv`

`PRINT_STOCK` is accepted as an ordered report checkpoint. The supplied output specification does not define a `stock.csv` file or columns, so this adapter does not invent an additional stock-output contract.

## Verification

Run the adapter's tests:

```powershell
python -m pytest tests/test_official_sample_pack.py -v
```

Then run the official pack:

```powershell
python run_official_pack.py --data-dir "<path-to-T068-PS-061-sample-data>" --output-dir "official_sample_outputs"
```

The adapter is a deterministic, database-independent evaluator/output adapter. It reads the supplied CSV files and simulates the command stream in memory; it does not import records into MySQL or replace the application's MySQL-backed service workflows. Use the separate guarded MySQL acceptance demo for persistence/transaction checks.

## Explicit interpretation notes requiring confirmation against the evaluator

1. **EC-02, chronic expiry boundary:** A chronic batch with exactly 30 days remaining is treated as ineligible. This interprets “within 30 days” as `days_remaining <= 30`.
2. **EC-03 versus BR-11:** `RX-0061` is 101 days of supply. The pack's EC-03 description uses it to illustrate `101 units -> 2 full packs`, but BR-11 limits a patient's rolling 90-day supply to 90 days. The adapter applies BR-11 and records `REJECTED_LIMIT`; `pending_units` still shows the 200-unit pack-rounded requirement. Ask the faculty which rule takes precedence if they expect RX-0061 to be dispensed.
3. **EC-06 return window:** The pack describes the return at day 7, 23:59 as within seven days. The adapter uses calendar-day comparison (`return_date - sale_date <= 7`) rather than a strict 168-hour comparison. The return is still rejected because exactly 60 days remain to expiry and the rule requires more than 60 days.
4. **OTC cap across brands:** The extra trap uses two different brand IDs in the same substitution group. The adapter counts OTC pack purchases by patient, day and substitution group, so a third pack of another brand in that group is rejected.
5. **Recall effective time versus command arrival:** The recall command can appear after a dispense command while carrying an earlier effective timestamp. When the recall is processed, earlier dispense records after that effective timestamp are retroactively added to `violations.csv`, and the batch is frozen for later commands. The input has no separate recall-arrival timestamp, so `detected_ts` uses the supplied effective timestamp.
6. **Other compliance flags:** `violations.csv` includes rejected duplicate, invalid-prescription, rolling-limit, OTC-limit and return events in addition to post-recall dispensing. The exact violation-code vocabulary is authored from the pack's examples because the pack does not provide expected output files.

The supplied sample pack explicitly says expected outputs are not provided. The six generated outputs must therefore be reviewed against BR-01–BR-12 and the planted scenarios; they are not asserted to be faculty-approved golden outputs.
