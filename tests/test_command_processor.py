import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.commands.command_processor import (
    CommandProcessor,
    _parse_parameter_values,
    build_default_handlers,
    to_json_value,
)


def test_valid_command_dispatches_parameters_and_returns_result():
    processor = CommandProcessor({"sum": lambda left, right: left + right})
    result = processor.process_line(
        '{"command_id":"C-01","command":"sum","parameters":{"left":2,"right":3}}',
        4,
    )
    assert result["line"] == 4
    assert result["command_id"] == "C-01"
    assert result["status"] == "SUCCESS"
    assert result["result"] == 5


def test_invalid_json_is_reported_without_raising():
    result = CommandProcessor({}).process_line('{"command":', 2)
    assert result["status"] == "ERROR"
    assert result["error"]["code"] == "INVALID_JSON"
    assert result["line"] == 2


def test_json_array_is_rejected_because_each_line_must_be_an_object():
    result = CommandProcessor({}).process_line('[1, 2]')
    assert result["error"]["code"] == "INVALID_COMMAND_OBJECT"


def test_missing_command_is_reported():
    result = CommandProcessor({}).process_line('{"parameters":{}}')
    assert result["error"]["code"] == "MISSING_COMMAND"


def test_parameters_must_be_an_object():
    result = CommandProcessor({"go": lambda: True}).process_line(
        '{"command":"go","parameters":[]}'
    )
    assert result["error"]["code"] == "INVALID_PARAMETERS"


def test_unknown_command_is_reported():
    result = CommandProcessor({}).process_line('{"command":"drop_database"}')
    assert result["error"]["code"] == "UNKNOWN_COMMAND"


def test_value_error_is_reported_as_business_rule_rejection():
    def reject():
        raise ValueError("REJECTED_LIMIT")

    result = CommandProcessor({"dispense": reject}).process_line(
        '{"command":"dispense"}'
    )
    assert result["error"]["code"] == "BUSINESS_RULE_REJECTED"
    assert result["error"]["message"] == "REJECTED_LIMIT"


def test_type_error_is_reported_as_invalid_parameters():
    result = CommandProcessor({"needs_id": lambda item_id: item_id}).process_line(
        '{"command":"needs_id","parameters":{}}'
    )
    assert result["error"]["code"] == "INVALID_PARAMETERS"


def test_iso_date_and_datetime_parameters_are_converted():
    values = _parse_parameter_values({
        "dispense_date": "2026-11-06",
        "prescription_date": "2026-11-05",
        "start_date": "2026-11-01",
        "end_date": "2026-11-06",
        "sale_at": "2026-11-06T10:15:00",
        "start_at": "2026-11-06T09:00:00",
        "end_at": "2026-11-06T18:00:00",
        "customer_id": 4,
    })
    assert values["dispense_date"] == date(2026, 11, 6)
    assert values["prescription_date"] == date(2026, 11, 5)
    assert values["start_date"] == date(2026, 11, 1)
    assert values["end_date"] == date(2026, 11, 6)
    assert values["sale_at"] == datetime(2026, 11, 6, 10, 15)
    assert values["start_at"] == datetime(2026, 11, 6, 9, 0)
    assert values["end_at"] == datetime(2026, 11, 6, 18, 0)
    assert values["customer_id"] == 4


def test_invalid_iso_date_is_rejected():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        _parse_parameter_values({"business_date": "06-11-2026"})


def test_json_serializer_preserves_decimal_as_string_and_dates_as_iso():
    @dataclass
    class Result:
        amount: Decimal
        business_date: date

    assert to_json_value(Result(Decimal("12.30"), date(2026, 11, 6))) == {
        "amount": "12.30",
        "business_date": "2026-11-06",
    }


def test_stream_continues_after_bad_command_and_counts_errors():
    processor = CommandProcessor({"echo": lambda value: value})
    source = io.StringIO(
        '{"command":"echo","parameters":{"value":"first"}}\n'
        '{not json}\n'
        '{"command":"echo","parameters":{"value":"third"}}\n'
    )
    target = io.StringIO()
    failures = processor.process_stream(source, target)
    rows = [json.loads(line) for line in target.getvalue().splitlines()]

    assert failures == 1
    assert [row["status"] for row in rows] == ["SUCCESS", "ERROR", "SUCCESS"]
    assert rows[0]["result"] == "first"
    assert rows[2]["result"] == "third"


def test_default_command_map_exposes_only_supported_service_operations():
    handlers = build_default_handlers()
    assert {
        "register_supplier",
        "register_customer",
        "register_doctor",
        "register_patient",
        "create_prescription",
        "register_drug",
        "receive_batch",
        "get_fefo_batches",
        "dispense_prescription_line",
        "otc_sale",
        "generate_bill",
        "process_customer_return",
        "request_supplier_return",
        "complete_supplier_return",
        "cancel_supplier_return",
        "recall_batch",
        "get_recall_violations",
        "run_end_of_day",
        "get_stock_report",
        "get_h1_register_report",
        "get_x_register_report",
        "get_inventory_movement_report",
    }.issubset(handlers)
