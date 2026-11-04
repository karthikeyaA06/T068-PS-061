# PS-061: Pharmacy Inventory Management System

## 1. Project Information

Project ID: PS-061

Project Title: Pharmacy Inventory with Batch Expiry,
Schedule-H Control and Substitution

Domain: Healthcare – Pharmacy

Difficulty: High

Programming Language: Python 3.10+

Database: MySQL

Architecture: Layered Architecture

Interface: Command-file driven

## 2. Introduction

The Pharmacy Inventory Management System is a backend
application designed to manage hospital retail pharmacy
operations.

The system manages drug registration, batch-wise inventory,
prescription validation, FEFO-based dispensing, controlled
drug restrictions, generic substitution, billing, GST,
returns and expiry management.

The system uses command files as input and generates
structured outputs and reports.

## 3. Project Objectives

1. Maintain accurate drug and batch inventory.
2. Implement FEFO-based stock dispensing.
3. Enforce Schedule H, H1 and X restrictions.
4. Support safe generic substitution.
5. Calculate bills with GST and applicable discounts.
6. Manage returns, recalls and expiry write-offs.
7. Generate reorder lists and compliance registers.

## 4. Project Scope

The system includes:

- Drug master management
- Batch and supplier management
- Prescription processing
- FEFO dispensing
- Schedule H/H1/X compliance
- Generic substitution
- Billing and GST
- Customer and supplier returns
- Recall management
- Expiry and stock reports
- End-of-day processing

The system does not include a graphical user interface.

## 5. Technology Stack

| Component | Technology |
|---|---|
| Programming | Python 3.14 |
| Database | MySQL 8.0 |
| Database Connector | mysql-connector-python |
| Testing | pytest |
| Version Control | Git |
| Repository | GitHub |

## 6. Glossary

| Term | Meaning |
|---|---|
| FEFO | First Expiry, First Out |
| MRP | Maximum Retail Price |
| GST | Goods and Services Tax |
| OTC | Over-the-Counter |
| H1 Register | Record of Schedule H1 transactions |
| Schedule X | Specially controlled drug category |
| Batch | Group of drug units manufactured together |
| Substitution | Replacing a prescribed brand with an eligible alternative |
| Partial Fill | Dispensing only available valid stock |
| Pending Line | Undispensed quantity awaiting fulfilment |
| Recall | Action to withdraw a batch from circulation |
| Write-off | Removal of expired inventory from usable stock |

## 7. Business Rule Register

| ID | Business Rule | Module |
|---|---|---|
| BR-01 | FEFO picking and expiry restrictions | Inventory |
| BR-02 | Quantity calculation and partial fills | Dispensing |
| BR-03 | Schedule H/H1/X restrictions and registers | Compliance |
| BR-04 | OTC daily customer limits | Sales |
| BR-05 | Generic substitution restrictions | Substitution |
| BR-06 | MRP, GST, loyalty discounts and rounding | Billing |
| BR-07 | Near-expiry alerts and expired write-offs | Expiry |
| BR-08 | Customer return policy | Returns |
| BR-09 | Stock-based reorder calculation | Inventory |
| BR-10 | Supplier returns and recall handling | Supplier |
| BR-11 | Rolling 90-day dispensing limits | Dispensing |
| BR-12 | Prescription validity and refill timing | Prescription |

## 8. System Architecture

The system follows a layered architecture:

1. Command Layer
2. Service Layer
3. Validation Layer
4. Repository Layer
5. Database Layer

## 9. Diagrams

- Class Diagram
- Batch State Diagram
- Prescription Line State Diagram
- Entity Relationship Diagram
- System Architecture Diagram

## 10. Edge Cases

All eight edge cases specified in the PS-061 problem
statement must be covered by automated tests.

## 11. Testing Strategy

Each business rule will have corresponding pytest test cases.
Integration tests will verify database operations and
complete command-driven workflows.

## 12. Conclusion

The proposed system provides a reliable backend engine
for pharmacy inventory, controlled drug compliance,
prescription dispensing and billing operations.