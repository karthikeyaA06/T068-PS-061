from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run_official_pack import SamplePackEngine, OUTPUT_COLUMNS

def locate_data_dir():
    import os
    configured = os.environ.get("PS061_SAMPLE_DATA_DIR")
    required = {"drugs.csv", "suppliers.csv", "batches.csv", "doctors.csv", "patients.csv", "prescriptions.csv", "prescription_lines.csv", "commands.txt"}
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend([
        ROOT / "sample_data" / "T068-PS-061-sample-data",
        ROOT / "Capstone_Sample_Data_Packs_Atria" / "T068-PS-061-sample-data",
        ROOT / "T068-PS-061-sample-data",
    ])
    for folder in ROOT.rglob("commands.txt"):
        candidates.append(folder.parent)
    for candidate in candidates:
        if candidate.is_dir() and all((candidate / name).is_file() for name in required):
            return candidate
    raise FileNotFoundError(
        "Official sample pack folder not found. Set PS061_SAMPLE_DATA_DIR or place "
        "T068-PS-061-sample-data under the repository root."
    )


DATA = locate_data_dir()


def run_pack(tmp_path):
    engine = SamplePackEngine(DATA)
    result = engine.run()
    engine.write_outputs(tmp_path, result)
    return engine, result


def rows_for(result, rx_id):
    return [r for r in result["dispense_lines"] if r["rx_id"] == rx_id]


def test_official_pack_loads_all_rows_and_commands(tmp_path):
    engine, result = run_pack(tmp_path)
    assert len(engine.drugs) == 120
    assert len(engine.suppliers) == 5
    assert len(engine.batches) == 323
    assert len(engine.doctors) == 25
    assert len(engine.patients) == 130
    assert len(engine.prescriptions) == 200
    assert sum(map(len, engine.lines_by_rx.values())) == 594
    assert result["command_total"] == 309
    assert result["errors"] == []


def test_required_output_files_and_headers_are_created(tmp_path):
    _, result = run_pack(tmp_path)
    for filename, columns in OUTPUT_COLUMNS.items():
        path = tmp_path / filename
        assert path.is_file()
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            assert next(reader) == columns


def test_fefo_tie_break_duplicate_and_exact_30_day_boundary(tmp_path):
    _, result = run_pack(tmp_path)
    rx30 = rows_for(result, "RX-0030")
    assert [r["batch_id"] for r in rx30 if r["command_line"] == 42] == ["BAT-0175", "BAT-0192"]
    assert rx30[-1]["reason_code"] == "DUPLICATE"
    rx106 = rows_for(result, "RX-0106")
    assert rx106[0]["batch_id"] == "BAT-0208"  # BAT-0003 expires exactly 30 days away.


def test_pack_rounding_and_90_day_limit_conflict_is_explicit(tmp_path):
    _, result = run_pack(tmp_path)
    assert rows_for(result, "RX-0060")[0]["units"] == 100
    rx61 = rows_for(result, "RX-0061")[0]
    # BR-11 caps a rolling request at 90 days; the source README's EC-03
    # separately uses 101 days to illustrate pack rounding to 200 units.
    assert rx61["status"] == "REJECTED"
    assert rx61["reason_code"] == "REJECTED_LIMIT"
    assert rx61["pending_units"] == 200


def test_substitution_near_expiry_and_schedule_x_rules(tmp_path):
    _, result = run_pack(tmp_path)
    substitute = rows_for(result, "RX-0075")[0]
    assert substitute["status"] == "SUBSTITUTED"
    assert substitute["dispensed_drug_id"] == "DRG-035"
    assert substitute["substitute_of"] == "DRG-034"

    bill = next(r for r in result["bills"] if r["rx_or_sale_id"] == "RX-0121")
    assert bill["discount_type"] == "NEAR_EXPIRY"
    assert bill["discount_amount"] == "10.40"  # 20%, not stacked with loyalty.

    assert rows_for(result, "RX-0133")[0]["reason_code"] == "X_SUPPLY_LIMIT"
    x_register = [r for r in result["registers"] if r["rx_id"] == "RX-0140"]
    assert x_register and x_register[0]["batch_no"]


def test_refill_return_and_recall_edge_cases(tmp_path):
    _, result = run_pack(tmp_path)
    rx13 = rows_for(result, "RX-0013")
    assert [r["reason_code"] for r in rx13 if r["status"] == "REJECTED"] == ["REFILL_TOO_EARLY", "REFILL_LIMIT"]
    assert any(r["status"] == "DISPENSED" and r["command_line"] == 62 for r in rx13)

    rx85 = [r for r in result["violations"] if r["rx_id"] == "RX-0085"]
    assert rx85 and rx85[0]["violation"] == "INSUFFICIENT_EXPIRY_REMAINING"

    rx141 = rows_for(result, "RX-0141")[0]
    assert rx141["status"] == "PARTIAL" and rx141["pending_units"] == 10
    recall = [r for r in result["violations"] if r["rx_id"] == "RX-0141"]
    assert recall and recall[0]["violation"] == "POST_RECALL_DISPENSE"


def test_otc_limit_and_invalid_prescription_traps(tmp_path):
    _, result = run_pack(tmp_path)
    assert any(r["rx_id"] == "OTC-0902" and r["reason_code"] == "OTC_LIMIT" for r in result["dispense_lines"])
    assert rows_for(result, "RX-0007")[0]["reason_code"] == "REJECTED_EXPIRED_RX"
    assert rows_for(result, "RX-0093")[0]["reason_code"] == "INVALID_DOCTOR"
    assert rows_for(result, "RX-0173")[0]["status"] == "PENDING"


def test_supplier_return_pending_excludes_reorder_and_writeoff_is_created(tmp_path):
    _, result = run_pack(tmp_path)
    eod = result["eod"]
    # BAT-0004 belongs to DRG-055. The pending supplier return prevents a
    # reorder for that drug on 2026-10-06.
    assert not any(r["date"] == "2026-10-06" and r["action"] == "REORDER" and r["drug_id"] == "DRG-055" for r in eod)
    assert any(r["date"] == "2026-10-01" and r["action"] == "WRITE_OFF" and r["batch_id"] == "BAT-0001" for r in eod)
