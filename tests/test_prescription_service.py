from datetime import date
import pytest

from app.services.prescription_service import PrescriptionService


def test_prescription_required_units_round_fraction_up():
    assert PrescriptionService.calculate_required_units("1.5", 7, 10, False) == 11


def test_prescription_full_pack_exact_pack_stays_exact():
    assert PrescriptionService.calculate_required_units(1, 10, 10, True) == 10


def test_prescription_full_pack_one_unit_over_rounds_up():
    assert PrescriptionService.calculate_required_units(1, 11, 10, True) == 20


def test_prescription_non_full_pack_is_not_rounded_to_pack():
    assert PrescriptionService.calculate_required_units(1, 11, 10, False) == 11


def test_prescription_quantity_rejects_invalid_values():
    with pytest.raises(ValueError):
        PrescriptionService.calculate_required_units(0, 10, 10, False)
    with pytest.raises(ValueError):
        PrescriptionService.calculate_required_units(1, 0, 10, False)
    with pytest.raises(ValueError):
        PrescriptionService.calculate_required_units(1, 10, 0, False)


def test_create_prescription_rejects_empty_lines_before_database_access():
    with pytest.raises(ValueError, match="non-empty list"):
        PrescriptionService().create_prescription(1, 1, date(2026, 11, 14), [])


def test_create_prescription_rejects_invalid_line_before_database_access():
    with pytest.raises(ValueError, match="drug_id"):
        PrescriptionService().create_prescription(
            1, 1, date(2026, 11, 14), [{"drug_id": 0, "dose_per_day": 1, "days_supply": 5}]
        )


class _FakeCursor:
    def __init__(self, drug_schedule="H"):
        self.drug_schedule = drug_schedule
        self.row = None
        self.lastrowid = 0
        self.line_inserts = 0
        self.closed = False

    def execute(self, sql, params=None):
        compact = " ".join(sql.lower().split())
        if "from doctors" in compact:
            self.row = {
                "doctor_id": 1,
                "registration_number": "REG-TEST-001",
                "is_active": True,
            }
        elif "from patients" in compact:
            self.row = {"patient_id": 2}
        elif compact.startswith("insert into prescriptions"):
            self.lastrowid = 100
            self.row = None
        elif "from drugs" in compact:
            self.row = {
                "drug_id": 3,
                "pack_size": 10,
                "sells_full_packs": True,
                "is_active": True,
                "schedule": self.drug_schedule,
            }
        elif compact.startswith("insert into prescription_lines"):
            self.lastrowid = 200
            self.line_inserts += 1
            self.row = None
        else:
            raise AssertionError(f"Unexpected SQL in fake cursor: {compact}")

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self, drug_schedule="H"):
        self.fake_cursor = _FakeCursor(drug_schedule)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def start_transaction(self):
        pass

    def cursor(self, dictionary=False):
        assert dictionary is True
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def is_connected(self):
        return not self.closed

    def close(self):
        self.closed = True


def test_create_prescription_persists_valid_line_and_decimal_dose(monkeypatch):
    import app.services.prescription_service as module

    connection = _FakeConnection(drug_schedule="H")
    monkeypatch.setattr(module, "get_connection", lambda: connection)
    result = PrescriptionService().create_prescription(
        doctor_id=1,
        patient_id=2,
        prescription_date=date.today(),
        lines=[{"drug_id": 3, "dose_per_day": "1.5", "days_supply": 7}],
    )
    assert result["status"] == "ACTIVE"
    assert result["lines"][0]["required_units"] == 20
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.fake_cursor.line_inserts == 1


def test_create_prescription_rejects_schedule_x_eight_day_supply(monkeypatch):
    import app.services.prescription_service as module

    connection = _FakeConnection(drug_schedule="X")
    monkeypatch.setattr(module, "get_connection", lambda: connection)
    with pytest.raises(ValueError, match="REJECTED_LIMIT"):
        PrescriptionService().create_prescription(
            doctor_id=1,
            patient_id=2,
            prescription_date=date.today(),
            lines=[{"drug_id": 3, "dose_per_day": 1, "days_supply": 8}],
        )
    assert connection.rolled_back is True
    assert connection.committed is False
    assert connection.fake_cursor.line_inserts == 0


def test_create_prescription_rejects_expired_schedule_h_prescription(monkeypatch):
    from datetime import timedelta
    import app.services.prescription_service as module

    connection = _FakeConnection(drug_schedule="H")
    monkeypatch.setattr(module, "get_connection", lambda: connection)
    with pytest.raises(ValueError, match="REJECTED_EXPIRED_RX"):
        PrescriptionService().create_prescription(
            doctor_id=1,
            patient_id=2,
            prescription_date=date.today() - timedelta(days=31),
            lines=[{"drug_id": 3, "dose_per_day": 1, "days_supply": 5}],
        )
    assert connection.rolled_back is True
    assert connection.fake_cursor.line_inserts == 0
