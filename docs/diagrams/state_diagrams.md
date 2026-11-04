
# PS-061 – State Diagrams

## 1. Batch Lifecycle State Diagram

```mermaid
stateDiagram-v2
    [*] --> RECEIVED

    RECEIVED --> AVAILABLE: Receipt validated

    AVAILABLE --> DEPLETED: Available quantity becomes zero

    AVAILABLE --> FROZEN: Recall or quarantine event

    AVAILABLE --> RETURNED: Eligible supplier return accepted

    AVAILABLE --> EXPIRED: Expiry month has passed

    FROZEN --> RETURNED: Recalled batch returned to supplier

    FROZEN --> EXPIRED: Expiry month has passed

    EXPIRED --> WRITTEN_OFF: First day of following month

    DEPLETED --> [*]
    RETURNED --> [*]
    WRITTEN_OFF --> [*]

    note right of FROZEN
      Dispensing is prohibited
      after the recall timestamp.
    end note

    note right of AVAILABLE
      FEFO selects eligible batches.
      NEAR_EXPIRY is a calculated flag,
      not a permanent lifecycle state.
    end note
```

## 2. Batch State Descriptions

| State | Description |
|---|---|
| RECEIVED | Stock batch has been received |
| AVAILABLE | Batch has usable stock |
| FROZEN | Batch cannot be dispensed |
| DEPLETED | Available stock is zero |
| RETURNED | Remaining stock has been returned to supplier |
| EXPIRED | Batch is past its expiry month |
| WRITTEN_OFF | Expired stock has been financially written off |

A batch is valid through the last calendar day
of its expiry month.

Expiry write-off occurs on the first day
of the following month.



## 3. Prescription Line State Diagram

```mermaid
stateDiagram-v2
    [*] --> NEW

    NEW --> VALIDATED: Prescription checks pass

    NEW --> REJECTED: Invalid prescription or limit exceeded

    VALIDATED --> DISPENSED: Full quantity dispensed

    VALIDATED --> PARTIALLY_FILLED: Some valid stock available

    VALIDATED --> PENDING: No valid stock available

    VALIDATED --> PENDING: NO_SUBSTITUTION prevents substitution

    PARTIALLY_FILLED --> PENDING: Shortfall recorded

    PENDING --> PARTIALLY_FILLED: Partial fulfilment before deadline

    PARTIALLY_FILLED --> DISPENSED: All required quantity fulfilled

    PENDING --> DISPENSED: Remaining quantity fulfilled

    PENDING --> EXPIRED: Seven-day pending period expires

    REJECTED --> [*]
    DISPENSED --> [*]
    EXPIRED --> [*]

    note right of PENDING
      Pending quantity is tracked.
      Standard partial-fill pending
      validity is 7 days.
    end note

    note right of REJECTED
      Store the rejection reason:
      REJECTED_LIMIT,
      REJECTED_EXPIRED_RX,
      or another validation failure.
    end note
```

## 4. Prescription State Descriptions

| State | Description |
|---|---|
| NEW | Prescription line is created |
| VALIDATED | Prescription and dispensing rules passed |
| PARTIALLY_FILLED | Some required units have been dispensed |
| PENDING | Outstanding quantity is awaiting fulfilment |
| DISPENSED | Entire required quantity has been dispensed |
| REJECTED | Dispensing is rejected |
| EXPIRED | Pending fulfilment period has ended |

## 5. Important Transition Rules

1. A prescription must pass validation before dispensing.
2. Partial dispensing occurs only when valid stock is insufficient.
3. The undispensed quantity is recorded as pending.
4. Pending partial-fill lines are valid for seven days.
5. A pending quantity fulfilled before its deadline completes the line.
6. A line with NO_SUBSTITUTION remains pending when the prescribed brand is unavailable.
7. Prescription validity, refill restrictions and rolling dispensing limits must be checked before every dispense.
```
