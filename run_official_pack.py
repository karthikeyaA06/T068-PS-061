#!/usr/bin/env python3
"""Run the official T068-PS-061 pipe-delimited sample pack.

This evaluator adapter reads the supplied CSV masters and commands.txt in strict
file order, simulates the inventory state, and writes the six CSV outputs required
by the sample-pack README. It is deliberately separate from the project's JSONL
service command runner: the official sample pack uses COMMAND|arg1|arg2 lines.

The adapter is deterministic and does not write to MySQL. It is intended for
sample-pack/evaluator compatibility and repeatable acceptance testing.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path
from typing import Any

CENT = Decimal("0.01")
ZERO = Decimal("0.00")

OUTPUT_COLUMNS = {
    "dispense_lines.csv": [
        "command_line", "rx_id", "line_no", "drug_id", "dispensed_drug_id",
        "batch_id", "units", "status", "reason_code", "substitute_of", "pending_units",
    ],
    "bills.csv": [
        "bill_id", "rx_or_sale_id", "line_no", "drug_id", "batch_id", "units",
        "mrp_amount", "discount_type", "discount_amount", "net_amount", "gst_pct",
        "gst_amount", "taxable_amount",
    ],
    "bill_totals.csv": [
        "bill_id", "bill_ts", "patient_id", "gross", "discount", "net", "rounding", "bill_total",
    ],
    "registers.csv": [
        "schedule", "entry_ts", "rx_id", "patient_id", "patient_name", "doctor_reg_no",
        "drug_id", "batch_no", "units",
    ],
    "eod.csv": ["date", "action", "drug_id", "batch_id", "units", "value"],
    "violations.csv": ["detected_ts", "batch_id", "rx_id", "dispense_ts", "violation"],
}


def as_bool(value: str) -> bool:
    value = str(value).strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(f"Expected true/false, got {value!r}")
    return value == "true"


def money(value: Decimal | str | int) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt_money(value: Decimal | str | int) -> str:
    return f"{money(value):.2f}"


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def expiry_last_day(expiry_month: str) -> date:
    y, m = map(int, expiry_month.split("-"))
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1) - timedelta(days=1)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


@dataclass
class BatchState:
    source: dict[str, str]
    remaining: int
    frozen: bool = False
    returned: bool = False
    supplier_return_pending: bool = False
    supplier_return_reason: str = ""
    recalled_at: datetime | None = None

    @property
    def batch_id(self) -> str:
        return self.source["batch_id"]

    @property
    def drug_id(self) -> str:
        return self.source["drug_id"]

    @property
    def batch_no(self) -> str:
        return self.source["batch_no"]

    @property
    def expiry(self) -> date:
        return expiry_last_day(self.source["expiry_month"])

    @property
    def received(self) -> date:
        return parse_date(self.source["received_date"])

    @property
    def purchase_price(self) -> Decimal:
        return Decimal(self.source["purchase_price"])


@dataclass
class Pick:
    batch_id: str
    drug_id: str
    units: int
    near_expiry: bool


class SamplePackEngine:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.drugs = {r["drug_id"]: r for r in read_csv_rows(data_dir / "drugs.csv")}
        self.suppliers = {r["supplier_id"]: r for r in read_csv_rows(data_dir / "suppliers.csv")}
        self.batches = {
            r["batch_id"]: BatchState(r, int(r["quantity_units"]))
            for r in read_csv_rows(data_dir / "batches.csv")
        }
        self.doctors = {r["doctor_reg_no"]: r for r in read_csv_rows(data_dir / "doctors.csv")}
        self.patients = {r["patient_id"]: r for r in read_csv_rows(data_dir / "patients.csv")}
        self.prescriptions = {r["rx_id"]: r for r in read_csv_rows(data_dir / "prescriptions.csv")}
        self.lines_by_rx: dict[str, list[dict[str, str]]] = defaultdict(list)
        for line in read_csv_rows(data_dir / "prescription_lines.csv"):
            self.lines_by_rx[line["rx_id"]].append(line)
        for rows in self.lines_by_rx.values():
            rows.sort(key=lambda x: int(x["line_no"]))

        self._validate_master_data()

        self.dispense_rows: list[dict[str, Any]] = []
        self.bill_rows: list[dict[str, Any]] = []
        self.bill_totals: list[dict[str, Any]] = []
        self.register_entries: list[dict[str, Any]] = []
        self.eod_rows: list[dict[str, Any]] = []
        self.violations: list[dict[str, Any]] = []

        self.rx_initial_done: set[str] = set()
        self.rx_first_dispense: dict[str, datetime] = {}
        self.rx_refill_count: defaultdict[str, int] = defaultdict(int)
        self.rx_bill_count: defaultdict[str, int] = defaultdict(int)
        self.line_first_picks: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        self.line_returned: defaultdict[tuple[str, int], int] = defaultdict(int)
        self.rx_group_supply: dict[tuple[str, str], list[tuple[datetime, Decimal]]] = defaultdict(list)
        self.otc_packs: defaultdict[tuple[str, str, date], int] = defaultdict(int)
        self.dispensed_batch_history: list[dict[str, Any]] = []
        self.recall_violations_seen: set[tuple[str, str, str]] = set()
        self.printed_register_keys: set[tuple[Any, ...]] = set()
        self.command_counts: defaultdict[str, int] = defaultdict(int)
        self.errors: list[tuple[int, str, str]] = []
        self.rejections: list[tuple[int, str, str]] = []
        self._returned_from_pick: defaultdict[tuple[str, int, int], int] = defaultdict(int)

    def _validate_master_data(self) -> None:
        """Fail fast on broken CSV references before any commands are applied."""
        for batch in self.batches.values():
            if batch.drug_id not in self.drugs:
                raise ValueError(f"Batch {batch.batch_id} references unknown drug {batch.drug_id}")
            if batch.source["supplier_id"] not in self.suppliers:
                raise ValueError(f"Batch {batch.batch_id} references unknown supplier {batch.source['supplier_id']}")
        for rx_id, rx in self.prescriptions.items():
            if rx["patient_id"] not in self.patients:
                raise ValueError(f"Prescription {rx_id} references unknown patient {rx['patient_id']}")
            if rx["doctor_reg_no"] not in self.doctors:
                raise ValueError(f"Prescription {rx_id} references unknown doctor {rx['doctor_reg_no']}")
            if rx_id not in self.lines_by_rx:
                raise ValueError(f"Prescription {rx_id} has no prescription lines")
        for rx_id, lines in self.lines_by_rx.items():
            if rx_id not in self.prescriptions:
                raise ValueError(f"Prescription line references unknown Rx {rx_id}")
            for line in lines:
                if line["drug_id"] not in self.drugs:
                    raise ValueError(f"Prescription line {rx_id}/{line['line_no']} references unknown drug {line['drug_id']}")

    def _required_units(self, drug: dict[str, str], dose: str, days: str) -> int:
        raw = Decimal(dose) * Decimal(days)
        units = int(raw.to_integral_value(rounding=ROUND_CEILING))
        if as_bool(drug["full_pack_only"]):
            pack = int(drug["pack_size"])
            units = ((units + pack - 1) // pack) * pack
        return units

    def _eligible_batches(self, drug_id: str, when: datetime, days_supply: int, *, otc: bool = False) -> list[BatchState]:
        candidates: list[BatchState] = []
        for batch in self.batches.values():
            if batch.drug_id != drug_id or batch.frozen or batch.returned or batch.supplier_return_pending:
                continue
            if batch.remaining <= 0 or batch.received > when.date() or batch.expiry < when.date():
                continue
            days_left = (batch.expiry - when.date()).days
            if otc:
                if days_left <= 30:
                    continue
            elif days_supply >= 30:
                if days_left <= 30:
                    continue
            elif days_left <= 7:
                continue
            candidates.append(batch)
        return sorted(candidates, key=lambda b: (b.expiry, b.received, b.batch_no))

    def _alloc(self, drug_id: str, when: datetime, quantity: int, days_supply: int, *, otc: bool = False) -> list[Pick]:
        drug = self.drugs[drug_id]
        pack_size = int(drug["pack_size"])
        full_pack = as_bool(drug["full_pack_only"])
        remaining = quantity
        picks: list[Pick] = []
        for batch in self._eligible_batches(drug_id, when, days_supply, otc=otc):
            available = batch.remaining
            if full_pack:
                available = (available // pack_size) * pack_size
            take = min(remaining, available)
            if full_pack:
                take = (take // pack_size) * pack_size
            if take <= 0:
                continue
            batch.remaining -= take
            days_left = (batch.expiry - when.date()).days
            picks.append(Pick(batch.batch_id, drug_id, take, 0 <= days_left <= 90))
            remaining -= take
            if remaining <= 0:
                break
        return picks

    def _rolling_days(self, patient_id: str, group_id: str, when: datetime, window_days: int) -> Decimal:
        start_date = when.date() - timedelta(days=window_days - 1)
        total = Decimal("0")
        for ts, days in self.rx_group_supply[(patient_id, group_id)]:
            if start_date <= ts.date() <= when.date():
                total += days
        return total

    def _add_violation(self, detected_ts: datetime, batch_id: str, rx_id: str,
                       dispense_ts: datetime, violation: str) -> None:
        self.violations.append({
            "detected_ts": detected_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "batch_id": batch_id,
            "rx_id": rx_id,
            "dispense_ts": dispense_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "violation": violation,
        })

    def _validation_reason(self, rx_id: str, line: dict[str, str], when: datetime, *, refill: bool) -> str | None:
        rx = self.prescriptions[rx_id]
        drug = self.drugs[line["drug_id"]]
        schedule = drug["schedule"]
        rx_date = parse_date(rx["rx_date"])
        age = (when.date() - rx_date).days
        doctor = self.doctors.get(rx["doctor_reg_no"])

        if schedule in {"H", "H1", "X"} and (
         doctor is None or not as_bool(doctor["registration_valid"])
):
         return "INVALID_DOCTOR"
        if age < 0:
            return "INVALID_PRESCRIPTION_DATE"
        if schedule in {"H", "H1"} and age > 30:
            return "REJECTED_EXPIRED_RX"
        if schedule == "X" and age > 7:
            return "REJECTED_EXPIRED_RX"
        days = int(line["days"])
        if schedule == "X" and days > 7:
            return "X_SUPPLY_LIMIT"
        if refill:
            if schedule == "X":
                return "REFILL_NOT_ALLOWED"
            allowed = int(rx["refills_allowed"])
            if self.rx_refill_count[rx_id] >= allowed:
                return "REFILL_LIMIT"
            first = self.rx_first_dispense.get(rx_id)
            if first is None:
                return "REFILL_WITHOUT_FIRST_DISPENSE"
            minimum_seconds = int(Decimal("0.8") * Decimal(days) * Decimal(24 * 60 * 60))
            if (when - first).total_seconds() < minimum_seconds:
                return "REFILL_TOO_EARLY"
            if schedule == "H1" and self.rx_refill_count[rx_id] >= 1:
                return "REFILL_LIMIT"

        # BR-11 counts supply by substitution group, so another brand in the
        # same molecule/strength/form group contributes to the same patient limit.
        group_id = drug["group_id"]
        limit = Decimal(30 if schedule == "H1" else 90)
        already = self._rolling_days(rx["patient_id"], group_id, when, 90)
        if already + Decimal(days) > limit:
            return "REJECTED_LIMIT"
        return None

    def _bill(self, bill_key: str, bill_ts: datetime, patient_id: str, line_no: int,
              prescribed_drug_id: str, pick: Pick, schedule: str) -> dict[str, Any]:
        drug = self.drugs[pick.drug_id]
        units = pick.units
        gross = money(Decimal(drug["mrp"]) * Decimal(units) / Decimal(int(drug["pack_size"])))
        patient = self.patients[patient_id]
        loyalty = as_bool(patient["loyalty_member"])
        loyalty_pct = Decimal("10") if schedule == "NONE" else Decimal("5") if schedule == "H" else Decimal("0")
        if pick.near_expiry:
            discount_type, discount_pct = "NEAR_EXPIRY", Decimal("20")
        elif loyalty and loyalty_pct > 0:
            discount_type, discount_pct = "LOYALTY", loyalty_pct
        else:
            discount_type, discount_pct = "NONE", Decimal("0")
        discount = money(gross * discount_pct / Decimal("100"))
        net = money(gross - discount)
        gst_pct = Decimal(drug["gst_pct"])
        gst = money(net * gst_pct / (Decimal("100") + gst_pct))
        taxable = money(net - gst)
        return {
            "bill_id": bill_key,
            "rx_or_sale_id": bill_key.removeprefix("BILL-").rsplit("-", 1)[0],
            "line_no": line_no,
            "drug_id": pick.drug_id,
            "batch_id": pick.batch_id,
            "units": units,
            "mrp_amount": fmt_money(gross),
            "discount_type": discount_type,
            "discount_amount": fmt_money(discount),
            "net_amount": fmt_money(net),
            "gst_pct": str(int(gst_pct)),
            "gst_amount": fmt_money(gst),
            "taxable_amount": fmt_money(taxable),
            "_gross": gross,
            "_discount": discount,
            "_net": net,
        }

    def _commit_bill(self, bill_key: str, bill_ts: datetime, patient_id: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        gross = money(sum((r["_gross"] for r in rows), Decimal("0")))
        discount = money(sum((r["_discount"] for r in rows), Decimal("0")))
        net = money(sum((r["_net"] for r in rows), Decimal("0")))
        total = net.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        rounding = money(total - net)
        for row in rows:
            self.bill_rows.append({k: v for k, v in row.items() if not k.startswith("_")})
        sale_or_rx = bill_key[5:]
        self.bill_totals.append({
            "bill_id": bill_key,
            "bill_ts": bill_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "patient_id": patient_id,
            "gross": fmt_money(gross),
            "discount": fmt_money(discount),
            "net": fmt_money(net),
            "rounding": fmt_money(rounding),
            "bill_total": fmt_money(total),
        })

    def _register(self, schedule: str, rx_id: str, line: dict[str, str], patient_id: str,
                  doctor_reg_no: str, when: datetime, picks: list[Pick]) -> None:
        if schedule not in {"H1", "X"}:
            return
        patient_name = self.patients[patient_id]["patient_name"]
        for pick in picks:
            batch = self.batches[pick.batch_id]
            self.register_entries.append({
                "schedule": schedule,
                "entry_ts": when.strftime("%Y-%m-%d %H:%M:%S"),
                "rx_id": rx_id,
                "patient_id": patient_id,
                "patient_name": patient_name,
                "doctor_reg_no": doctor_reg_no,
                "drug_id": pick.drug_id,
                "batch_no": batch.batch_no,
                "units": pick.units,
            })

    def _dispense_line(self, command_line: int, rx_id: str, line: dict[str, str], when: datetime,
                       refill: bool, bill_id: str) -> tuple[list[Pick], list[dict[str, Any]]]:
        rx = self.prescriptions[rx_id]
        original_drug_id = line["drug_id"]
        original_drug = self.drugs[original_drug_id]
        schedule = original_drug["schedule"]
        line_no = int(line["line_no"])
        reason = self._validation_reason(rx_id, line, when, refill=refill)
        if reason:
            self.dispense_rows.append({
                "command_line": command_line, "rx_id": rx_id, "line_no": line_no,
                "drug_id": original_drug_id, "dispensed_drug_id": "", "batch_id": "",
                "units": 0, "status": "REJECTED", "reason_code": reason,
                "substitute_of": "", "pending_units": self._required_units(original_drug, line["dose_per_day"], line["days"]),
            })
            return [], []

        needed = self._required_units(original_drug, line["dose_per_day"], line["days"])
        days = int(line["days"])
        prescribed_picks = self._alloc(original_drug_id, when, needed, days)
        dispensed_drug_id = original_drug_id
        substitute_of = ""
        picks = prescribed_picks
        substituted = False

        # Substitute only if the prescribed brand has no eligible stock at all.
        if not picks:
            if schedule != "X" and not as_bool(rx["no_substitution"]):
                candidates = []
                for candidate in self.drugs.values():
                    if candidate["group_id"] != original_drug["group_id"] or candidate["drug_id"] == original_drug_id:
                        continue
                    if candidate["schedule"] == "X":
                        continue
                    if Decimal(candidate["mrp"]) > Decimal(original_drug["mrp"]):
                        continue
                    available = self._eligible_batches(candidate["drug_id"], when, days)
                    if available:
                        candidates.append((Decimal(candidate["mrp"]), candidate["brand_name"].casefold(), candidate))
                for _, _, candidate in sorted(candidates, key=lambda x: (x[0], x[1])):
                    candidate_id = candidate["drug_id"]
                    candidate_needed = self._required_units(candidate, line["dose_per_day"], line["days"])
                    candidate_picks = self._alloc(candidate_id, when, candidate_needed, days)
                    if candidate_picks:
                        picks = candidate_picks
                        dispensed_drug_id = candidate_id
                        substitute_of = original_drug_id
                        substituted = True
                        break

        delivered = sum(p.units for p in picks)
        pending = max(0, needed - delivered)
        status = "SUBSTITUTED" if substituted else "PARTIAL" if pending else "DISPENSED"
        reason_code = "NO_SUBSTITUTION" if not picks and as_bool(rx["no_substitution"]) else "STOCK_SHORTFALL" if pending and picks else "NO_ELIGIBLE_STOCK" if pending else ""

        if picks:
            # Supply recorded for BR-11 is proportional to units actually supplied.
            group_id = original_drug["group_id"]
            actual_days = Decimal(delivered) / Decimal(line["dose_per_day"])
            self.rx_group_supply[(rx["patient_id"], group_id)].append((when, actual_days))
            self._register(schedule if not substituted else self.drugs[dispensed_drug_id]["schedule"],
                           rx_id, line, rx["patient_id"], rx["doctor_reg_no"], when, picks)
            bill_rows = []
            for pick in picks:
                self.dispense_rows.append({
                    "command_line": command_line, "rx_id": rx_id, "line_no": line_no,
                    "drug_id": original_drug_id, "dispensed_drug_id": dispensed_drug_id,
                    "batch_id": pick.batch_id, "units": pick.units, "status": status,
                    "reason_code": reason_code, "substitute_of": substitute_of,
                    "pending_units": pending,
                })
                record = {
                    "rx_id": rx_id, "line_no": line_no, "batch_id": pick.batch_id,
                    "drug_id": pick.drug_id, "units": pick.units, "when": when,
                    "dispensed_drug_id": dispensed_drug_id,
                }
                if not refill:
                    self.line_first_picks[(rx_id, line_no)].append(record)
                self.dispensed_batch_history.append(record)
                bill_rows.append(self._bill(bill_id, when, rx["patient_id"], line_no, original_drug_id, pick, self.drugs[pick.drug_id]["schedule"]))
        else:
            bill_rows = []
            self.dispense_rows.append({
                "command_line": command_line, "rx_id": rx_id, "line_no": line_no,
                "drug_id": original_drug_id, "dispensed_drug_id": "", "batch_id": "",
                "units": 0, "status": "PENDING", "reason_code": reason_code or "NO_ELIGIBLE_STOCK",
                "substitute_of": "", "pending_units": needed,
            })
        return picks, bill_rows

    def _reject_rx(self, command_line: int, rx_id: str, reason: str, when: datetime | None = None) -> None:
        self.rejections.append((command_line, reason, rx_id))
        if when is not None:
            self._add_violation(when, "", rx_id, when, reason)
        for line in self.lines_by_rx[rx_id]:
            drug = self.drugs[line["drug_id"]]
            needed = self._required_units(drug, line["dose_per_day"], line["days"])
            self.dispense_rows.append({
                "command_line": command_line, "rx_id": rx_id, "line_no": int(line["line_no"]),
                "drug_id": line["drug_id"], "dispensed_drug_id": "", "batch_id": "",
                "units": 0, "status": "REJECTED", "reason_code": reason,
                "substitute_of": "", "pending_units": needed,
            })

    def _process_rx_command(self, line_no: int, parts: list[str], refill: bool) -> None:
        rx_id, ts_text = parts[1], parts[2]
        when = parse_ts(ts_text)
        if rx_id not in self.prescriptions or rx_id not in self.lines_by_rx:
            self.errors.append((line_no, "UNKNOWN_RX", rx_id))
            return
        if not refill and rx_id in self.rx_initial_done:
            self._reject_rx(line_no, rx_id, "DUPLICATE", when)
            return
        if refill and rx_id not in self.rx_first_dispense:
            self._reject_rx(line_no, rx_id, "REFILL_WITHOUT_FIRST_DISPENSE", when)
            return

        # Prescription-wide failures have already been handled above.
# Drug-specific validation happens independently inside _dispense_line.
# One rejected medicine line must not reject other valid lines.

        self.rx_bill_count[rx_id] += 1
        bill_id = f"BILL-{rx_id}-{self.rx_bill_count[rx_id]}"
        command_bill_rows: list[dict[str, Any]] = []
        command_picks: dict[int, list[Pick]] = {}
        for rx_line in self.lines_by_rx[rx_id]:
            picks, bill_rows = self._dispense_line(line_no, rx_id, rx_line, when, refill, bill_id)
            command_picks[int(rx_line["line_no"])] = picks
            command_bill_rows.extend(bill_rows)
        self._commit_bill(bill_id, when, self.prescriptions[rx_id]["patient_id"], command_bill_rows)
        if not refill:
            self.rx_initial_done.add(rx_id)
            if any(command_picks.values()):
                self.rx_first_dispense[rx_id] = when
        else:
            if any(command_picks.values()):
                self.rx_refill_count[rx_id] += 1

    def _process_otc(self, line_no: int, parts: list[str]) -> None:
        sale_id, patient_id, ts_text, drug_id, packs_text = parts[1:]
        when = parse_ts(ts_text)
        if patient_id not in self.patients or drug_id not in self.drugs:
            self.errors.append((line_no, "UNKNOWN_PATIENT_OR_DRUG", sale_id))
            return
        drug = self.drugs[drug_id]
        packs = int(packs_text)
        pack_size = int(drug["pack_size"])
        units = packs * pack_size
        group_id = drug["group_id"]
        key = (patient_id, group_id, when.date())
        if drug["schedule"] != "NONE":
            self.dispense_rows.append({
                "command_line": line_no, "rx_id": sale_id, "line_no": 1,
                "drug_id": drug_id, "dispensed_drug_id": "", "batch_id": "", "units": 0,
                "status": "REJECTED", "reason_code": "PRESCRIPTION_REQUIRED",
                "substitute_of": "", "pending_units": units,
            })
            self.rejections.append((line_no, "PRESCRIPTION_REQUIRED", sale_id))
            self._add_violation(when, "", sale_id, when, "PRESCRIPTION_REQUIRED")
            return
        if self.otc_packs[key] + packs > 2:
            self.dispense_rows.append({
                "command_line": line_no, "rx_id": sale_id, "line_no": 1,
                "drug_id": drug_id, "dispensed_drug_id": "", "batch_id": "", "units": 0,
                "status": "REJECTED", "reason_code": "OTC_LIMIT",
                "substitute_of": "", "pending_units": units,
            })
            self.rejections.append((line_no, "OTC_LIMIT", sale_id))
            self._add_violation(when, "", sale_id, when, "OTC_LIMIT")
            return
        if as_bool(drug["full_pack_only"]) is False or units % pack_size == 0:
            pass
        else:
            raise ValueError("OTC full-pack quantity is invalid")
        picks = self._alloc(drug_id, when, units, 1, otc=True)
        delivered = sum(p.units for p in picks)
        pending = units - delivered
        status = "PARTIAL" if pending else "DISPENSED"
        reason = "STOCK_SHORTFALL" if pending else ""
        bill_id = f"BILL-{sale_id}-1"
        bill_rows = []
        for pick in picks:
            self.dispense_rows.append({
                "command_line": line_no, "rx_id": sale_id, "line_no": 1,
                "drug_id": drug_id, "dispensed_drug_id": drug_id, "batch_id": pick.batch_id,
                "units": pick.units, "status": status, "reason_code": reason,
                "substitute_of": "", "pending_units": pending,
            })
            record = {"rx_id": sale_id, "line_no": 1, "batch_id": pick.batch_id,
                      "drug_id": drug_id, "units": pick.units, "when": when,
                      "dispensed_drug_id": drug_id}
            self.dispensed_batch_history.append(record)
            bill_rows.append(self._bill(bill_id, when, patient_id, 1, drug_id, pick, "NONE"))
        if not picks:
            self.dispense_rows.append({
                "command_line": line_no, "rx_id": sale_id, "line_no": 1,
                "drug_id": drug_id, "dispensed_drug_id": "", "batch_id": "", "units": 0,
                "status": "PENDING", "reason_code": "NO_ELIGIBLE_STOCK", "substitute_of": "",
                "pending_units": units,
            })
        self._commit_bill(bill_id, when, patient_id, bill_rows)
        self.otc_packs[key] += packs if not pending else (delivered // pack_size)

    def _reject_customer_return(self, line_no: int, rx_id: str, reason: str,
                                when: datetime, picks: list[dict[str, Any]]) -> None:
        self.rejections.append((line_no, reason, rx_id))
        batch_id = picks[0]["batch_id"] if picks else ""
        dispense_ts = picks[0]["when"] if picks else when
        self._add_violation(when, batch_id, rx_id, dispense_ts, reason)

    def _customer_return(self, line_no: int, parts: list[str]) -> None:
        rx_id, line_no_text, return_ts_text, units_text, opened_text = parts[1:]
        line_no_int = int(line_no_text)
        when = parse_ts(return_ts_text)
        units = int(units_text)
        key = (rx_id, line_no_int)
        picks = self.line_first_picks.get(key, [])
        if not picks or units <= 0:
            self._reject_customer_return(line_no, rx_id, "CUSTOMER_RETURN_NO_ORIGINAL_DISPENSE", when, picks)
            return
        rx = self.prescriptions[rx_id]
        line = next((x for x in self.lines_by_rx[rx_id] if int(x["line_no"]) == line_no_int), None)
        if line is None:
            self._reject_customer_return(line_no, rx_id, "CUSTOMER_RETURN_UNKNOWN_LINE", when, picks)
            return
        drug = self.drugs[line["drug_id"]]
        if drug["schedule"] in {"H1", "X"}:
            self._reject_customer_return(line_no, rx_id, "SCHEDULE_NON_RETURNABLE", when, picks)
            return
        if as_bool(opened_text):
            self._reject_customer_return(line_no, rx_id, "OPENED_STRIPS_NOT_RETURNABLE", when, picks)
            return
        sale_date = min(x["when"].date() for x in picks)
        # The supplied EC-06 explicitly treats any time on calendar day 7,
        # including 23:59, as within the seven-day return window.
        age_days = (when.date() - sale_date).days
        if age_days < 0 or age_days > 7:
            self._reject_customer_return(line_no, rx_id, "RETURN_WINDOW_EXPIRED", when, picks)
            return
        already = self.line_returned[key]
        total_original = sum(x["units"] for x in picks)
        if units + already > total_original:
            self._reject_customer_return(line_no, rx_id, "RETURN_EXCEEDS_DISPENSED_UNITS", when, picks)
            return

        # Validate the expiry condition across the complete allocation before
        # restoring any stock, so a multi-batch return is atomic.
        available_allocations = []
        still_to_return = units
        for index, pick in enumerate(picks):
            previously_returned = self._returned_from_pick[(rx_id, line_no_int, index)]
            available_from_pick = pick["units"] - previously_returned
            if available_from_pick <= 0:
                continue
            take = min(still_to_return, available_from_pick)
            batch = self.batches[pick["batch_id"]]
            days_left = (batch.expiry - when.date()).days
            if days_left <= 60:
                self._reject_customer_return(line_no, rx_id, "INSUFFICIENT_EXPIRY_REMAINING", when, picks)
                return
            available_allocations.append((index, batch, take))
            still_to_return -= take
            if still_to_return <= 0:
                break
        if still_to_return:
            self._reject_customer_return(line_no, rx_id, "RETURN_EXCEEDS_DISPENSED_UNITS", when, picks)
            return
        for index, batch, take in available_allocations:
            batch.remaining += take
            self._returned_from_pick[(rx_id, line_no_int, index)] += take
        self.line_returned[key] += units

    def _supplier_return(self, line_no: int, parts: list[str]) -> None:
        batch_id, ts_text, reason = parts[1:]
        when = parse_ts(ts_text)
        batch = self.batches.get(batch_id)
        if batch is None:
            self.errors.append((line_no, "UNKNOWN_BATCH", batch_id))
            return
        ever_dispensed = any(x["batch_id"] == batch_id for x in self.dispensed_batch_history)
        days_left = (batch.expiry - when.date()).days
        if not batch.recalled_at and (days_left < 0 or days_left >= 90 or ever_dispensed):
            self.rejections.append((line_no, "SUPPLIER_RETURN_NOT_ELIGIBLE", batch_id))
            self._add_violation(when, batch_id, "", when, "SUPPLIER_RETURN_NOT_ELIGIBLE")
            return
        batch.supplier_return_pending = True
        batch.supplier_return_reason = reason

    def _recall(self, line_no: int, parts: list[str]) -> None:
        batch_id, ts_text, reason = parts[1:]
        effective = parse_ts(ts_text)
        batch = self.batches.get(batch_id)
        if batch is None:
            self.errors.append((line_no, "UNKNOWN_BATCH", batch_id))
            return
        batch.frozen = True
        batch.recalled_at = effective
        for pick in self.dispensed_batch_history:
            if pick["batch_id"] == batch_id and pick["when"] > effective:
                key = (batch_id, pick["rx_id"], pick["when"].isoformat())
                if key not in self.recall_violations_seen:
                    self.recall_violations_seen.add(key)
                    self._add_violation(effective, batch_id, pick["rx_id"], pick["when"], "POST_RECALL_DISPENSE")

    def _end_of_day(self, line_no: int, parts: list[str]) -> None:
        business_date = parse_date(parts[1])
        # Near-expiry and write-off decisions use end-of-day date.
        for batch in sorted(self.batches.values(), key=lambda b: b.batch_id):
            if batch.remaining <= 0 or batch.returned or batch.supplier_return_pending:
                continue
            days_left = (batch.expiry - business_date).days
            if not batch.frozen and 0 <= days_left <= 90:
                self.eod_rows.append({
                    "date": business_date.isoformat(), "action": "NEAR_EXPIRY_FLAG",
                    "drug_id": batch.drug_id, "batch_id": batch.batch_id,
                    "units": batch.remaining, "value": "",
                })
            if batch.expiry < business_date:
                qty = batch.remaining
                drug = self.drugs[batch.drug_id]
                pack_size = int(drug["pack_size"])
                value = money(batch.purchase_price * Decimal(qty) / Decimal(pack_size))
                self.eod_rows.append({
                    "date": business_date.isoformat(), "action": "WRITE_OFF",
                    "drug_id": batch.drug_id, "batch_id": batch.batch_id,
                    "units": qty, "value": fmt_money(value),
                })
                batch.remaining = 0
        for drug_id, drug in sorted(self.drugs.items()):
            # BR-09 excludes a drug while any supplier return for one of its
            # batches remains pending, regardless of the batch's FEFO status.
            if any(b.drug_id == drug_id and b.supplier_return_pending for b in self.batches.values()):
                continue
            valid_stock = 0
            for batch in self.batches.values():
                if batch.drug_id != drug_id or batch.frozen or batch.returned or batch.supplier_return_pending:
                    continue
                if batch.expiry >= business_date and batch.received <= business_date:
                    valid_stock += batch.remaining
            minimum = int(drug["min_stock_units"])
            if valid_stock < minimum:
                pack_size = int(drug["pack_size"])
                base = 3 * minimum - valid_stock
                reorder = ((base + pack_size - 1) // pack_size) * pack_size
                self.eod_rows.append({
                    "date": business_date.isoformat(), "action": "REORDER",
                    "drug_id": drug_id, "batch_id": "", "units": reorder, "value": "",
                })

    def _print_register(self, schedule: str, as_of: date) -> None:
        # The pack specifies register rows "per PRINT_REGISTER" command.
        # Therefore each print command emits its as-of snapshot; a later print
        # may repeat earlier register entries because the output schema has no
        # separate snapshot-date column.
        for entry in self.register_entries:
            if entry["schedule"] == schedule and parse_ts(entry["entry_ts"]).date() <= as_of:
                self._printed_register_rows.append(entry.copy())

    def run(self) -> dict[str, Any]:
        commands_path = self.data_dir / "commands.txt"
        self._printed_register_rows: list[dict[str, Any]] = []
        with commands_path.open("r", encoding="utf-8-sig") as handle:
            for line_no, raw in enumerate(handle, start=1):
                text = raw.strip()
                if not text or text.startswith("#"):
                    continue
                parts = text.split("|")
                command = parts[0]
                self.command_counts[command] += 1
                expected = {
                    "DISPENSE": 3, "REFILL": 3, "OTC_SALE": 6,
                    "CUSTOMER_RETURN": 6, "SUPPLIER_RETURN": 4,
                    "RECALL": 4, "END_OF_DAY": 2, "PRINT_STOCK": 2,
                    "PRINT_REGISTER": 3,
                }
                if command not in expected or len(parts) != expected[command]:
                    self.errors.append((line_no, "INVALID_COMMAND_SHAPE", text))
                    continue
                try:
                    if command == "DISPENSE":
                        self._process_rx_command(line_no, parts, refill=False)
                    elif command == "REFILL":
                        self._process_rx_command(line_no, parts, refill=True)
                    elif command == "OTC_SALE":
                        self._process_otc(line_no, parts)
                    elif command == "CUSTOMER_RETURN":
                        self._customer_return(line_no, parts)
                    elif command == "SUPPLIER_RETURN":
                        self._supplier_return(line_no, parts)
                    elif command == "RECALL":
                        self._recall(line_no, parts)
                    elif command == "END_OF_DAY":
                        self._end_of_day(line_no, parts)
                    elif command == "PRINT_REGISTER":
                        schedule = parts[1].upper()
                        if schedule not in {"H1", "X"}:
                            self.errors.append((line_no, "INVALID_REGISTER_SCHEDULE", schedule))
                        else:
                            self._print_register(schedule, parse_date(parts[2]))
                    elif command == "PRINT_STOCK":
                        # The pack README defines no stock.csv output contract.
                        # The command is accepted as a state/report checkpoint.
                        parse_date(parts[1])
                except Exception as exc:
                    self.errors.append((line_no, type(exc).__name__, str(exc)))

        return {
            "commands": dict(self.command_counts),
            "command_total": sum(self.command_counts.values()),
            "errors": self.errors,
            "rejections": self.rejections,
            "dispense_lines": self.dispense_rows,
            "bills": self.bill_rows,
            "bill_totals": self.bill_totals,
            "registers": self._printed_register_rows,
            "eod": self.eod_rows,
            "violations": self.violations,
        }

    def write_outputs(self, output_dir: Path, result: dict[str, Any]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping = {
            "dispense_lines.csv": result["dispense_lines"],
            "bills.csv": result["bills"],
            "bill_totals.csv": result["bill_totals"],
            "registers.csv": result["registers"],
            "eod.csv": result["eod"],
            "violations.csv": result["violations"],
        }
        for filename, rows in mapping.items():
            with (output_dir / filename).open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS[filename], extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the official T068-PS-061 pipe-delimited sample pack.")
    parser.add_argument("--data-dir", required=True, help="Folder containing all seven CSV files and commands.txt")
    parser.add_argument("--output-dir", default="sample_pack_outputs", help="Directory for the six required CSV outputs")
    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    required = ["drugs.csv", "suppliers.csv", "batches.csv", "doctors.csv", "patients.csv", "prescriptions.csv", "prescription_lines.csv", "commands.txt"]
    missing = [name for name in required if not (data_dir / name).is_file()]
    if missing:
        parser.error(f"Missing sample-pack files in {data_dir}: {', '.join(missing)}")
    engine = SamplePackEngine(data_dir)
    result = engine.run()
    engine.write_outputs(output_dir, result)
    print(f"Processed {result['command_total']} commands from {data_dir}")
    print("Command counts:", result["commands"])
    print(f"Generated {len(OUTPUT_COLUMNS)} output CSV files in {output_dir}")
    print(f"Dispense lines: {len(result['dispense_lines'])}; bill lines: {len(result['bills'])}; bills: {len(result['bill_totals'])}; registers: {len(result['registers'])}; EOD rows: {len(result['eod'])}; violations: {len(result['violations'])}")
    print(f"Input/processing errors: {len(result['errors'])}")
    print(f"Expected business rejections: {len(result['rejections'])}")
    for issue in result["errors"][:30]:
        print("ERROR", *issue)
    for rejection in result["rejections"][:20]:
        print("REJECTED", *rejection)
    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
