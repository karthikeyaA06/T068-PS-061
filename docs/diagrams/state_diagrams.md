
# PS-061 – Pharmacy Inventory Management System
# State Diagrams

## 1. Batch Lifecycle State Diagram

```mermaid
stateDiagram-v2
    [*] --> RECEIVED

    RECEIVED --> AVAILABLE: Batch receipt validated

    AVAILABLE --> DEPLETED: Available stock becomes zero

    AVAILABLE --> FROZEN: Recall event received

    AVAILABLE --> RETURNED: Entire eligible batch returned

    AVAILABLE --> EXPIRED: Last valid expiry day has passed

    FROZEN --> RETURNED: Recalled batch returned to supplier

    FROZEN --> EXPIRED: Last valid expiry day has passed

    EXPIRED --> WRITTEN_OFF: First day of following month

    DEPLETED --> [*]
    RETURNED --> [*]
    WRITTEN_OFF --> [*]

    note right of AVAILABLE
        FEFO selects eligible batches.
        Near-expiry is a calculated flag,
        not a permanent batch state.
    end note

    note right of FROZEN
        No dispensing is permitted
        after the recall timestamp.
    end note

    note right of EXPIRED
        Expired stock cannot be dispensed.
        Write-off uses purchase price.
    end note
```

## 2. Batch State Descriptions

| State | Description |
|---|---|
| RECEIVED | Stock batch has been received |
| AVAILABLE | Batch contains usable stock |
| FROZEN | Batch is blocked due to recall |
| DEPLETED | Available stock becomes zero |
| RETURNED | Entire remaining eligible batch is returned |
| EXPIRED | Batch has passed its last valid expiry day |
| WRITTEN_OFF | Expired inventory has been financially written off |

Important rules:

- A batch remains valid through the last calendar day of its expiry month.
- Expiry write-off happens on the first day of the following month.
- Partial supplier returns are recorded as quantity movements; the batch need not enter RETURNED state until all remaining stock has been returned.
- A recall event must be recorded with its timestamp.
- Near-expiry status is calculated according to the business date.

---

## 3. Prescription Line State Diagram

```mermaid
stateDiagram-v2
    [*] --> NEW

    NEW --> REJECTED: Prescription validation fails

    NEW --> VALIDATED: Prescription validation succeeds

    VALIDATED --> DISPENSED: Full required quantity dispensed

    VALIDATED --> PARTIALLY_FILLED: Some valid stock available

    VALIDATED --> PENDING: No valid stock available

    VALIDATED --> PENDING: NO_SUBSTITUTION prevents substitution

    PARTIALLY_FILLED --> DISPENSED: Remaining quantity fulfilled

    PARTIALLY_FILLED --> PENDING: Shortfall recorded

    PENDING --> PARTIALLY_FILLED: Some pending quantity fulfilled

    PENDING --> DISPENSED: Entire pending quantity fulfilled

    PENDING --> EXPIRED: Seven-day pending validity expires

    REJECTED --> [*]
    DISPENSED --> [*]
    EXPIRED --> [*]

    note right of PARTIALLY_FILLED
        Some quantity has been dispensed.
        The remaining quantity is tracked
        separately as pending.
    end note

    note right of PENDING
        A partial-fill pending line
        remains valid for seven days.
    end note

    note right of REJECTED
        Examples:
        REJECTED_LIMIT
        REJECTED_EXPIRED_RX
    end note
```

## 4. Prescription Line State Descriptions

| State | Description |
|---|---|
| NEW | Prescription line has been created |
| VALIDATED | Prescription checks have passed |
| PARTIALLY_FILLED | Some required quantity has been dispensed |
| PENDING | Remaining quantity awaits fulfilment |
| DISPENSED | Entire required quantity has been dispensed |
| REJECTED | Dispensing request has been rejected |
| EXPIRED | Pending fulfilment validity has expired |

## 5. Important State Transition Rules

1. Prescription validation must occur before dispensing.
2. A prescription line may be rejected when validity, schedule or quantity restrictions fail.
3. Partial fill is permitted only when eligible stock is insufficient.
4. The dispensed quantity and remaining pending quantity must be stored separately.
5. A partial-fill pending line is valid for seven days.
6. Pending quantities may be fulfilled before the validity deadline.
7. Schedule X no-refill restrictions and Schedule H1 refill restrictions must be checked independently.
8. A NO_SUBSTITUTION line cannot be substituted when the prescribed brand is unavailable.

The specification does not separately define the pending validity period for NO_SUBSTITUTION lines. This remains an open design decision.
