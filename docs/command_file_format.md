# PS-061 JSONL Command-File Format

## Purpose

The project brief specifies a command-file-driven backend and identifies JSONL commands. This document defines the command envelope implemented in this repository. It is a project-level interface contract, not a claim that the faculty's undistributed evaluator schema uses identical field names. Compare it with any official sample before submission/evaluation.

## One command per line

Each non-empty UTF-8 line must contain one JSON object:

```json
{
  "command_id": "C001",
  "command": "get_fefo_batches",
  "parameters": {
    "drug_id": 1,
    "dispense_date": "2026-11-06",
    "days_supply": 10
  }
}
```

- `command_id` is optional and is copied to the output for traceability.
- `command` is a required, case-sensitive operation name.
- `parameters` is an optional JSON object; it defaults to `{}`.
- Dates use ISO `YYYY-MM-DD`; datetimes use ISO 8601, e.g. `2026-11-06T10:30:00`.
- Monetary Decimal values are emitted as JSON strings to preserve exact decimal precision.

## Supported operation names

| Command | Required parameters | Effect |
|---|---|---|
| `register_supplier` | `supplier_name`; optional `contact_person`, `phone`, `email`, `address` | Creates supplier master data |
| `register_customer` | `customer_name`; optional `phone`, `loyalty_member` | Creates customer and loyalty record |
| `register_doctor` | `registration_number`, `doctor_name`; optional `is_active` | Creates doctor registration record |
| `register_patient` | `patient_name`; optional `contact` | Creates patient record |
| `create_prescription` | `doctor_id`, `patient_id`, `prescription_date`, `lines` | Creates prescription header and calculated quantity lines |
| `register_drug` | `molecule`, `strength`, `dosage_form`, `brand_name`, `schedule`, `mrp`, `gst_rate`, `pack_size`, `min_stock`; optional `sells_full_packs`, `controlled_substance` | Writes drug master data |
| `receive_batch` | `drug_id`, `supplier_id`, `batch_number`, `expiry_month` (`YYYY-MM`), `quantity`, `purchase_price`; optional `notes` | Adds stock and a receipt movement |
| `get_fefo_batches` | `drug_id`, `dispense_date`, `days_supply` | Read-only FEFO query |
| `dispense_prescription_line` | `prescription_line_id`, `customer_id`; optional `dispense_date` | Dispenses against a prescription line |
| `otc_sale` | `customer_id`, `drug_id`, `quantity`; optional `sale_at` | Writes OTC dispense and stock movements |
| `generate_bill` | `dispense_id` | Writes a bill for an existing dispense |
| `process_customer_return` | `bill_line_id`, `quantity`, `unopened`; optional `returned_at` | Writes a return/refund record and restores original batch stock |
| `request_supplier_return` | `batch_id`; optional `quantity`, `reason`, `requested_at` | Reserves batch stock for supplier return |
| `complete_supplier_return` | `supplier_return_id`; optional `completed_at` | Removes reserved stock and completes return |
| `cancel_supplier_return` | `supplier_return_id` | Cancels a pending return and releases reservation |
| `recall_batch` | `batch_id`, `reason`; optional `recalled_at` | Freezes a batch and records recall timestamp |
| `get_recall_violations` | `recall_id` | Read-only query for post-recall dispensing rows |
| `run_end_of_day` | `business_date` | Writes expiry write-offs and reorder suggestions; returns near-expiry alerts |

## Master-data and prescription-intake examples

The commands below are examples; use unique names/registration numbers in your database. Run each JSON object as one line in a UTF-8 `.jsonl` file. Use the IDs returned by the successful commands when preparing dependent records.

```json
{"command_id":"M001","command":"register_supplier","parameters":{"supplier_name":"Demo Supplier","phone":"9000000000"}}
{"command_id":"M002","command":"register_customer","parameters":{"customer_name":"Demo Customer","phone":"9000000001","loyalty_member":true}}
{"command_id":"M003","command":"register_doctor","parameters":{"registration_number":"DEMO-REG-001","doctor_name":"Demo Doctor"}}
{"command_id":"M004","command":"register_patient","parameters":{"patient_name":"Demo Patient","contact":"9000000002"}}
```

After registering a drug and receiving an eligible batch, create a prescription using the returned doctor, patient and drug IDs:

```json
{"command_id":"P001","command":"create_prescription","parameters":{"doctor_id":1,"patient_id":1,"prescription_date":"2026-11-14","lines":[{"drug_id":1,"dose_per_day":"1.0","days_supply":10,"no_substitution":false}]}}
```

The IDs above are illustrative only. Do not assume they match existing database records. `create_prescription` calculates required units from dose, days, pack size and the drug's full-pack flag in a single transaction.

## Run the command file

```powershell
python run_commands.py input.jsonl --output output.jsonl
```

Omit `--output` to write results to standard output. The process continues after an invalid line. Its exit code is `0` when every non-empty line succeeds, `1` when one or more command lines fail, and `2` for input/output file errors.

## Output envelope

Success:

```json
{"line":1,"command_id":"C001","command":"get_fefo_batches","status":"SUCCESS","result":[]}
```

Failure:

```json
{"line":2,"command_id":"C002","command":"dispense_prescription_line","status":"ERROR","error":{"code":"BUSINESS_RULE_REJECTED","message":"REJECTED_LIMIT"}}
```

Error codes include `INVALID_JSON`, `INVALID_COMMAND_OBJECT`, `MISSING_COMMAND`, `INVALID_PARAMETERS`, `UNKNOWN_COMMAND`, `BUSINESS_RULE_REJECTED`, and `COMMAND_FAILED`.

## Safety and compatibility notes

- Commands that write records must be run against a disposable/demo database until full integration testing is complete.
- The processor uses an explicit allow-list; arbitrary Python methods or SQL are never accepted as command names.
- The processor is unit-tested for parsing, validation, serialization and per-line error isolation.
- The exact official evaluator command sample and expected output were not present in the files reviewed. The implemented envelope must be compared with that sample before claiming evaluator compatibility.
