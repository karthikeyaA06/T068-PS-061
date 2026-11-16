# PS-061 – Pharmacy Inventory with Batch Expiry, Schedule-H Control and Substitution — Sample Data Pack

Prepared by 10 SECONDS for Team T068.

## Files

| File | What it holds | Row count |
|---|---|---|
| `drugs.csv` | 120 drugs (brands) in 40 molecule-strength-form substitution groups | 120 data rows |
| `suppliers.csv` | 5 suppliers | 5 data rows |
| `batches.csv` | Stock receipts as batches (opening stock and receipts during the period) | 323 data rows |
| `doctors.csv` | Prescribing doctors with registration validity | 25 data rows |
| `patients.csv` | Patients with loyalty membership | 130 data rows |
| `prescriptions.csv` | Prescriptions (header) | 200 data rows |
| `prescription_lines.csv` | Prescription lines (drug, dose per day, days) | 594 data rows |
| `commands.txt` | Dispenses, refills, OTC sales, customer and supplier returns, recalls, end-of-day runs and report prints over 60 days | 309 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable / not supplied" and only occurs in columns whose notes say so.

### `drugs.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| drug_id | string | DRG-nnn | — | — |
| brand_name | string | — | — | fictional brands |
| group_id | string | GRP-nn | — | substitution group |
| molecule | string | — | — | — |
| strength | string | — | — | — |
| form | enum | — | TAB, CAP, SYRUP, SACHET, INHALER, PEN | — |
| schedule | enum | — | NONE, H, H1, X | — |
| mrp | decimal | Rs per pack, GST inclusive | — | — |
| pack_size | int | units per pack | — | MRP per unit = mrp / pack_size |
| gst_pct | int | % | 5, 12 | — |
| full_pack_only | bool | — | — | true = sold only in whole packs |
| min_stock_units | int | units | — | reorder trigger |
| controlled | bool | — | — | H1 / X |
| manufacturer | string | — | — | — |

### `suppliers.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| supplier_id | string | SUP-nn | — | — |
| supplier_name | string | — | — | — |
| city | string | — | — | — |

### `batches.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| batch_id | string | BAT-nnnn | — | internal id, numbered by received_date |
| drug_id | string | — | drugs.csv | — |
| batch_no | string | — | — | manufacturer batch number (FEFO tie-break) |
| expiry_month | string | YYYY-MM | — | valid through the last day of the month |
| quantity_units | int | units | — | received quantity |
| purchase_price | decimal | Rs per pack | — | write-off value |
| supplier_id | string | — | suppliers.csv | — |
| received_date | date | — | — | stock usable from 00:00 of this date |

### `doctors.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| doctor_reg_no | string | KMC-nnnnnn | — | — |
| doctor_name | string | — | — | — |
| council | string | — | — | — |
| registration_valid | bool | — | — | false = invalid registration |

### `patients.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| patient_id | string | PAT-nnnn | — | — |
| patient_name | string | — | — | — |
| gender | enum | — | M, F | — |
| age | int | years | — | — |
| mobile | string | 10 digits | — | — |
| loyalty_member | bool | — | — | — |

### `prescriptions.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| rx_id | string | RX-nnnn | — | — |
| patient_id | string | — | patients.csv | — |
| doctor_reg_no | string | — | doctors.csv | — |
| rx_date | date | — | — | — |
| no_substitution | bool | — | — | doctor wrote NO_SUBSTITUTION |
| refills_allowed | int | — | 0, 1 | — |

### `prescription_lines.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| rx_id | string | — | prescriptions.csv | — |
| line_no | int | — | — | 1-based within the Rx |
| drug_id | string | — | drugs.csv | prescribed brand |
| dose_per_day | decimal | units/day, 1 dp | — | — |
| days | int | days | — | >= 30 = chronic, < 30 = acute |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An empty argument (two adjacent `|`) means "not supplied". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `DISPENSE` | `rx_id|dispense_ts` | dispense every line of the prescription |
| `REFILL` | `rx_id|dispense_ts` | refill of a previously dispensed prescription |
| `OTC_SALE` | `sale_id|patient_id|sale_ts|drug_id|packs` | over-the-counter sale without prescription |
| `CUSTOMER_RETURN` | `rx_id|line_no|return_ts|units|opened` | return against the line's first dispense; opened true/false |
| `SUPPLIER_RETURN` | `batch_id|ts|reason` | return a batch to its supplier |
| `RECALL` | `batch_id|recall_effective_ts|reason` | recall notice; may arrive after its effective time — the line position is the arrival |
| `END_OF_DAY` | `date` | near-expiry flags, write-offs, reorder list |
| `PRINT_STOCK` | `date` | stock by batch at end of that date |
| `PRINT_REGISTER` | `schedule|date` | H1 or X register up to that date |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Two batches with the same expiry month: tie broken by receipt date then batch number**
  - RX-0030: Glenlin 500 mg 3/day x 15 days = 45 units; three batches expire 2027-03 — pick AMX4471 (received 2026-08-20) first (30 units), then AMX4468 before AMX4470 (both received 2026-09-03; batch number decides) for the remaining 15 — `batches.csv rows 175, 191, 192; commands.txt line 42`
- **EC-02 Batch expiring in exactly 30 days for a 30-day chronic prescription**
  - RX-0106: chronic 30-day Rx dispensed 2026-10-01; FEFO batch expires 2026-10 (valid through 2026-10-31 = exactly 30 days away) — decide 'within 30 days' consistently (the other batch expires 2027-09) — `batches.csv row 3; commands.txt line 155`
- **EC-03 Required units exactly equal to one pack versus one unit over**
  - RX-0060: 2/day x 50 days = 100 units = exactly 1 pack of 100; RX-0061: 1/day x 101 days = 101 units → 2 full packs (full_pack_only) — `prescription_lines.csv rows 175, 176`
- **EC-04 Substitute brand with MRP exactly equal to prescribed MRP**
  - RX-0075: Glentor 40 mg (MRP 146.00) has no stock at all; group brands in stock: Feblin 40 mg at exactly the same MRP (eligible, <=) and Sunlin 40 mg at MRP 160.00 (not eligible) — substitute Feblin 40 mg and record both names — `drugs.csv DRG-034 (row 34), DRG-035 (row 35); commands.txt line 111`
- **EC-05 Loyalty 10% versus near-expiry 20% on the same line**
  - RX-0121 for loyalty member PAT-0005: Sunzol 500 mg (schedule NONE) only batch expires 2026-12 (87 days away → NEAR_EXPIRY 20%); loyalty 10% does not stack — 20% applies — `batches.csv row 2; commands.txt line 182`
- **EC-06 Return on day 7 at 23:59 with 60 days to expiry exactly**
  - RX-0085: dispensed 2026-09-24 10:00 from a batch expiring 2026-11 (valid through 2026-11-30); unopened return at 2026-10-01 23:59 (day 7) — within the 7 days, but the batch has exactly 60 days to expiry, not > 60 → return REJECTED — `commands.txt line 124 and line 163`
- **EC-07 Schedule X prescription for 8 days supply**
  - RX-0133: Schedule X Neodex 10 mg prescribed for 8 days — over the 7-day supply limit, must be REJECTED; RX-0140 (Schedule X, exactly 7 days) is dispensed and its X-register entry must carry the batch number — `prescription_lines.csv row 386; commands.txt line 201 and line 213`
- **EC-08 Recall event arriving after a partial dispense from that batch on the same day**
  - RX-0141 (NO_SUBSTITUTION, 30 units needed): only BAT-0190 (20 units) of Birotor 10 mg → partial fill of 20 + PENDING 10 at 2026-10-12 11:20; the RECALL line comes later in the file but is effective from 10:45 the same day — the 11:20 dispense is a VIOLATION to report and the batch is frozen — `commands.txt line 214 and line 218`
- **Extra traps (not in the brief, but realistic):**
  - RX-0173: Schedule X brand Arisran 0.2 mg out of stock while Birolin 0.2 mg is in stock — Schedule X is never substituted: line PENDING — `commands.txt line 261`
  - PAT-0033: OTC 2 packs at 10:05 and 1 more pack of the same molecule at 18:40 on 2026-09-12 — the 3rd pack in a day needs a prescription (REJECTED) — `commands.txt lines 54, 59`
  - RX-0007: Schedule H Rx dated 2026-09-03 presented 2026-10-04 (31 days) — REJECTED_EXPIRED_RX — `commands.txt line 172`
  - RX-0093: Schedule H Rx from KMC-126111 whose registration is not valid — REJECTED — `commands.txt line 132`
  - RX-0013 (H1, 10 days, 1 refill): REFILL on day 7 (< 80% of 10 days) REJECTED; on day 8 (= 80%) accepted and H1-registered; a further REFILL REJECTED (max 1) — `commands.txt line 56, line 62, line 128`
  - PAT-0069: Clonazepam (H1) 20 days on 2026-09-08 then another brand for 15 days on 2026-09-20 — 35 days of an H1 drug in a rolling 90-day window (> 30) → REJECTED_LIMIT — `commands.txt line 34 and line 97`
  - BAT-0004: SUPPLIER_RETURN of a never-dispensed batch with 86 days to expiry — accepted; Primamet 4 mg stock then falls below min stock but is excluded from that day's reorder (return pending) — `commands.txt line 187`
  - RX-0030 DISPENSE sent twice (4 minutes apart) — the second must be rejected, stock moves once — `commands.txt line 43`
  - BAT-0001 (Calmet 500 mg) expires 2026-09 (valid through 2026-09-30) — any remaining units are written off at purchase price on 2026-10-01 — `batches.csv row 1`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `dispense_lines.csv`

One row per batch pick (a line split over two batches gives two rows), in command order.

Columns, in order: `command_line`, `rx_id`, `line_no`, `drug_id`, `dispensed_drug_id`, `batch_id`, `units`, `status`, `reason_code`, `substitute_of`, `pending_units`

### `bills.csv`

One row per bill line.

Columns, in order: `bill_id`, `rx_or_sale_id`, `line_no`, `drug_id`, `batch_id`, `units`, `mrp_amount`, `discount_type`, `discount_amount`, `net_amount`, `gst_pct`, `gst_amount`, `taxable_amount`

### `bill_totals.csv`

One row per bill.

Columns, in order: `bill_id`, `bill_ts`, `patient_id`, `gross`, `discount`, `net`, `rounding`, `bill_total`

### `registers.csv`

H1 and X register entries per PRINT_REGISTER.

Columns, in order: `schedule`, `entry_ts`, `rx_id`, `patient_id`, `patient_name`, `doctor_reg_no`, `drug_id`, `batch_no`, `units`

### `eod.csv`

End-of-day actions per END_OF_DAY.

Columns, in order: `date`, `action`, `drug_id`, `batch_id`, `units`, `value`

### `violations.csv`

Recall violations and other compliance flags.

Columns, in order: `detected_ts`, `batch_id`, `rx_id`, `dispense_ts`, `violation`

Binding choices: bill_id = BILL-<rx_id or sale_id>-<n> (n = 1 for the first dispense, 2 for a refill…). Dispense `status` is DISPENSED, PARTIAL, PENDING, SUBSTITUTED or REJECTED (reason_code e.g. REJECTED_EXPIRED_RX, REJECTED_LIMIT, INVALID_DOCTOR, X_SUPPLY_LIMIT, OTC_LIMIT, DUPLICATE). discount_type NONE, LOYALTY, NEAR_EXPIRY. eod `action` NEAR_EXPIRY_FLAG, WRITE_OFF or REORDER (units = reorder quantity in whole packs x pack size).
