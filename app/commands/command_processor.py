"""JSON Lines command processing for the PS-061 backend.

Each non-empty input line is one JSON object:
    {"command_id": "C001", "command": "register_drug", "parameters": {...}}

One structured JSON result is emitted for every non-empty input line. Errors on
one line do not stop later commands from being processed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Iterable, Mapping, TextIO


_DATE_FIELDS = {"dispense_date", "business_date"}
_DATETIME_FIELDS = {
    "sale_at",
    "returned_at",
    "requested_at",
    "completed_at",
    "recalled_at",
}


def _parse_parameter_values(parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Convert documented ISO date/time parameter strings to Python values."""
    parsed = dict(parameters)
    for key in _DATE_FIELDS:
        value = parsed.get(key)
        if isinstance(value, str):
            try:
                parsed[key] = date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"'{key}' must use YYYY-MM-DD format.") from exc
    for key in _DATETIME_FIELDS:
        value = parsed.get(key)
        if isinstance(value, str):
            try:
                parsed[key] = datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(
                    f"'{key}' must be an ISO-8601 datetime, e.g. 2026-11-06T10:30:00."
                ) from exc
    return parsed


def to_json_value(value: Any) -> Any:
    """Convert service results into JSON-safe values without losing money precision."""
    if is_dataclass(value):
        return to_json_value(asdict(value))
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class CommandProcessor:
    """Validate and dispatch JSONL commands through an explicit allow-list."""

    def __init__(self, handlers: Mapping[str, Callable[..., Any]]):
        if not isinstance(handlers, Mapping):
            raise TypeError("handlers must be a mapping of command names to callables.")
        self.handlers = dict(handlers)
        if any(not isinstance(name, str) or not callable(handler)
               for name, handler in self.handlers.items()):
            raise ValueError("Every command handler must have a name and be callable.")

    def process_line(self, raw_line: str, line_number: int = 1) -> dict[str, Any]:
        command_id = None
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            return {
                "line": line_number,
                "command_id": None,
                "status": "ERROR",
                "error": {"code": "INVALID_JSON", "message": exc.msg},
            }

        if not isinstance(payload, dict):
            return {
                "line": line_number,
                "command_id": None,
                "status": "ERROR",
                "error": {
                    "code": "INVALID_COMMAND_OBJECT",
                    "message": "Each JSONL line must contain one JSON object.",
                },
            }

        command_id = payload.get("command_id")
        command = payload.get("command")
        parameters = payload.get("parameters", {})

        if not isinstance(command, str) or not command.strip():
            return self._error(
                line_number, command_id, "MISSING_COMMAND",
                "A non-empty 'command' string is required.",
            )
        command = command.strip()

        if not isinstance(parameters, dict):
            return self._error(
                line_number, command_id, "INVALID_PARAMETERS",
                "'parameters' must be a JSON object.",
            )

        handler = self.handlers.get(command)
        if handler is None:
            return self._error(
                line_number, command_id, "UNKNOWN_COMMAND",
                f"Unsupported command '{command}'.",
            )

        try:
            arguments = _parse_parameter_values(parameters)
            result = handler(**arguments)
            return {
                "line": line_number,
                "command_id": command_id,
                "command": command,
                "status": "SUCCESS",
                "result": to_json_value(result),
            }
        except TypeError as exc:
            return self._error(
                line_number, command_id, "INVALID_PARAMETERS", str(exc), command
            )
        except ValueError as exc:
            return self._error(
                line_number, command_id, "BUSINESS_RULE_REJECTED", str(exc), command
            )
        except Exception as exc:  # Keep the file moving; report this command only.
            return self._error(
                line_number,
                command_id,
                "COMMAND_FAILED",
                f"{type(exc).__name__}: {exc}",
                command,
            )

    @staticmethod
    def _error(line_number, command_id, code, message, command=None):
        result = {
            "line": line_number,
            "command_id": command_id,
            "status": "ERROR",
            "error": {"code": code, "message": str(message)},
        }
        if command is not None:
            result["command"] = command
        return result

    def process_stream(self, input_stream: TextIO, output_stream: TextIO) -> int:
        """Process non-empty JSONL lines; return the number of failed commands."""
        error_count = 0
        for line_number, raw_line in enumerate(input_stream, start=1):
            if not raw_line.strip():
                continue
            result = self.process_line(raw_line, line_number)
            if result["status"] == "ERROR":
                error_count += 1
            output_stream.write(json.dumps(result, ensure_ascii=False) + "\n")
        return error_count


def build_default_handlers() -> dict[str, Callable[..., Any]]:
    """Build the supported command map. Services are created lazily per command."""
    from app.services.batch_service import BatchService
    from app.services.billing_service import BillingService
    from app.services.dispensing_service import DispensingService
    from app.services.drug_service import DrugService
    from app.services.inventory_service import InventoryService
    from app.services.operational_workflow_service import OperationalWorkflowService
    from app.services.otc_service import OTCSalesService

    return {
        "register_drug": lambda **p: DrugService().register_drug(**p),
        "receive_batch": lambda **p: BatchService().receive_batch(**p),
        "get_fefo_batches": lambda **p: InventoryService().get_fefo_batches(**p),
        "dispense_prescription_line": lambda **p: DispensingService().dispense_prescription_line(**p),
        "otc_sale": lambda **p: OTCSalesService().sell(**p),
        "generate_bill": lambda dispense_id: BillingService().generate_bill(dispense_id),
        "process_customer_return": lambda **p: OperationalWorkflowService().process_customer_return(**p),
        "request_supplier_return": lambda **p: OperationalWorkflowService().request_supplier_return(**p),
        "complete_supplier_return": lambda **p: OperationalWorkflowService().complete_supplier_return(**p),
        "cancel_supplier_return": lambda **p: OperationalWorkflowService().cancel_supplier_return(**p),
        "recall_batch": lambda **p: OperationalWorkflowService().recall_batch(**p),
        "get_recall_violations": lambda recall_id: OperationalWorkflowService().get_recall_violations(recall_id),
        "run_end_of_day": lambda **p: OperationalWorkflowService().run_end_of_day(**p),
    }
