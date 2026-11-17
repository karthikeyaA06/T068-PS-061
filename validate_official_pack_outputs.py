#!/usr/bin/env python3
"""Validate T068-PS-061 official sample-pack outputs against planted scenarios.

This is a regression checker for the documented edge cases. It does not compare
against faculty golden outputs (none were supplied in the sample-pack README).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

EXPECTED_HEADERS = {
    "dispense_lines.csv": "command_line,rx_id,line_no,drug_id,dispensed_drug_id,batch_id,units,status,reason_code,substitute_of,pending_units".split(","),
    "bills.csv": "bill_id,rx_or_sale_id,line_no,drug_id,batch_id,units,mrp_amount,discount_type,discount_amount,net_amount,gst_pct,gst_amount,taxable_amount".split(","),
    "bill_totals.csv": "bill_id,bill_ts,patient_id,gross,discount,net,rounding,bill_total".split(","),
    "registers.csv": "schedule,entry_ts,rx_id,patient_id,patient_name,doctor_reg_no,drug_id,batch_no,units".split(","),
    "eod.csv": "date,action,drug_id,batch_id,units,value".split(","),
    "violations.csv": "detected_ts,batch_id,rx_id,dispense_ts,violation".split(","),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="official_sample_outputs")
    parser.add_argument("--data-dir", default="T068-PS-061-sample-data")
    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    data_dir = Path(args.data_dir)

    missing = [name for name in EXPECTED_HEADERS if not (out_dir / name).is_file()]
    if missing:
        parser.error(f"Missing output file(s): {', '.join(missing)}")

    outputs: dict[str, list[dict[str, str]]] = {}
    checks: list[tuple[str, bool, str]] = []

    for filename, expected in EXPECTED_HEADERS.items():
        with (out_dir / filename).open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            actual = reader.fieldnames or []
            rows = list(reader)
        outputs[filename] = rows
        checks.append((f"{filename} exact header", actual == expected, f"rows={len(rows)}"))
        required_key_fields = [x for x in expected if x not in {"batch_id", "dispensed_drug_id", "substitute_of", "reason_code", "value", "rounding"}]
        no_missing = all(all(str(row.get(col, "")).strip() != "" for col in required_key_fields) for row in rows)
        checks.append((f"{filename} required cells populated", no_missing, f"rows={len(rows)}"))

    dl = outputs["dispense_lines.csv"]
    bills = outputs["bills.csv"]
    totals = outputs["bill_totals.csv"]
    regs = outputs["registers.csv"]
    eod = outputs["eod.csv"]
    violations = outputs["violations.csv"]

    def rx_rows(rx_id: str) -> list[dict[str, str]]:
        return [r for r in dl if r["rx_id"] == rx_id]

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    # EC-01: expiry/receipt/batch tie-break and duplicate dispense.
    r = rx_rows("RX-0030")
    add("EC-01 FEFO tie-break order", len(r) == 3 and [(x["batch_id"], x["units"]) for x in r[:2]] == [("BAT-0175", "30"), ("BAT-0192", "15")], str([(x["batch_id"], x["units"]) for x in r]))
    add("EC-01 duplicate request rejected", len(r) == 3 and r[2]["status"] == "REJECTED" and r[2]["reason_code"] == "DUPLICATE", r[-1]["reason_code"] if r else "no rows")

    # EC-02: exactly-30-day chronic batch excluded.
    batch_map = {r["batch_id"]: r for r in read_csv(data_dir / "batches.csv")}
    r = rx_rows("RX-0106")
    picked = batch_map.get(r[0]["batch_id"], {}) if r else {}
    add("EC-02 exact-30-day chronic batch excluded", len(r) == 1 and picked.get("expiry_month") == "2027-09", f"picked={picked.get('batch_id')} expiry={picked.get('expiry_month')}")

    # EC-03: exact-pack quantity and one-over pack rounding. The sample pack
    # creates a specification conflict: 101-day supply rounds to 200 units for
    # a full-pack-only drug, but BR-11's 90-day cap rejects it.
    r60, r61 = rx_rows("RX-0060"), rx_rows("RX-0061")
    add("EC-03 exact 100-unit pack", len(r60) == 1 and r60[0]["units"] == "100" and r60[0]["status"] == "DISPENSED", str(r60))
    add("EC-03 101-day request rounded to 200 before BR-11 rejection", len(r61) == 1 and r61[0]["status"] == "REJECTED" and r61[0]["reason_code"] == "REJECTED_LIMIT" and r61[0]["pending_units"] == "200", str(r61))

    # EC-04: equal-MRP same-group substitute.
    r = rx_rows("RX-0075")
    add("EC-04 equal-MRP substitute selected", len(r) == 1 and r[0]["dispensed_drug_id"] == "DRG-035" and r[0]["substitute_of"] == "DRG-034", str(r))

    # EC-05: near expiry discount overrides loyalty.
    r = [x for x in bills if x["bill_id"] == "BILL-RX-0121-1"]
    add("EC-05 20-percent near-expiry discount overrides loyalty", len(r) == 1 and r[0]["discount_type"] == "NEAR_EXPIRY" and r[0]["discount_amount"] == "10.40", str(r))

    # EC-06 is a return rejection, therefore it is represented in violations.csv,
    # not dispense_lines.csv.
    r = [x for x in violations if x["rx_id"] == "RX-0085" and x["violation"] == "INSUFFICIENT_EXPIRY_REMAINING"]
    add("EC-06 day-7 23:59 return at exactly 60 expiry days rejected", len(r) == 1 and r[0]["detected_ts"] == "2026-10-01 23:59:00", str(r))

    # EC-07: X 8-day limit and exactly-7-day X register with batch number.
    r133, r140 = rx_rows("RX-0133"), [x for x in regs if x["rx_id"] == "RX-0140"]
    add("EC-07 Schedule X 8-day supply rejected", len(r133) == 1 and r133[0]["reason_code"] == "X_SUPPLY_LIMIT", str(r133))
    add("EC-07 Schedule X 7-day dispense registered with batch number", bool(r140) and all(x["schedule"] == "X" and x["units"] == "7" and bool(x["batch_no"]) for x in r140), f"register snapshot rows={len(r140)}")

    # EC-08: late-arriving recall flags the earlier same-day partial dispense.
    r141 = rx_rows("RX-0141")
    v141 = [x for x in violations if x["rx_id"] == "RX-0141" and x["violation"] == "POST_RECALL_DISPENSE"]
    add("EC-08 partial 20/30 dispensed and pending 10", len(r141) == 1 and r141[0]["status"] == "PARTIAL" and r141[0]["units"] == "20" and r141[0]["pending_units"] == "10", str(r141))
    add("EC-08 late recall flags post-effective-time dispense", len(v141) == 1 and v141[0]["detected_ts"] == "2026-10-12 10:45:00" and v141[0]["dispense_ts"] == "2026-10-12 11:20:00", str(v141))

    # Extra traps.
    r = rx_rows("RX-0173")
    add("Extra: Schedule X is not substituted", len(r) == 1 and r[0]["status"] == "PENDING" and not r[0]["dispensed_drug_id"], str(r))
    r = rx_rows("OTC-0902")
    add("Extra: third OTC pack rejected", len(r) == 1 and r[0]["reason_code"] == "OTC_LIMIT", str(r))
    r = rx_rows("RX-0007")
    add("Extra: expired Schedule H prescription rejected", len(r) == 1 and r[0]["reason_code"] == "REJECTED_EXPIRED_RX", str(r))
    r = rx_rows("RX-0093")
    add("Extra: invalid doctor rejected", len(r) == 1 and r[0]["reason_code"] == "INVALID_DOCTOR", str(r))
    r = rx_rows("RX-0013")
    add("Extra: refill too early, one refill accepted, next refill rejected", sum(x["reason_code"] == "REFILL_TOO_EARLY" for x in r) == 1 and sum(x["reason_code"] == "REFILL_LIMIT" for x in r) == 1 and sum(x["status"] == "DISPENSED" for x in r) == 2, str([(x["command_line"], x["status"], x["reason_code"]) for x in r]))
    add("Extra: H1 35-day rolling supply rejected", any(x["rx_id"] == "RX-0067" and x["reason_code"] == "REJECTED_LIMIT" for x in dl), "PAT-0069, shared Clonazepam group")
    add("Extra: pending supplier return suppresses reorder", not any(x["date"] == "2026-10-06" and x["drug_id"] == "DRG-055" and x["action"] == "REORDER" for x in eod), "BAT-0004 pending from 2026-10-06")
    add("Extra: BAT-0001 written off on 2026-10-01", any(x["date"] == "2026-10-01" and x["batch_id"] == "BAT-0001" and x["action"] == "WRITE_OFF" and x["units"] == "45" and x["value"] == "82.08" for x in eod), "45 units; purchase-cost valuation Rs 82.08")

    passed = sum(ok for _, ok, _ in checks)
    failed = len(checks) - passed
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'} | {name}" + (f" | {detail}" if detail and not ok else ""))
    print(f"\nOFFICIAL SAMPLE PACK OUTPUT AUDIT: {passed}/{len(checks)} checks passed")
    print(f"Rows: dispense={len(dl)}, bills={len(bills)}, bill_totals={len(totals)}, registers={len(regs)}, eod={len(eod)}, violations={len(violations)}")
    if failed:
        print(f"Failed checks: {failed}")
        return 1
    print("Note: this validates planted scenarios, not the faculty's hidden field-for-field golden output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
