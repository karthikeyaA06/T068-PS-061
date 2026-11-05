
-- =====================================================
-- PS-061 PHARMACY INVENTORY MANAGEMENT SYSTEM
-- WEEK 2: PRESCRIPTION AND DISPENSING SCHEMA
-- MySQL 8.0
-- =====================================================

USE pharmacy_inventory;


-- =====================================================
-- TABLE 1: DOCTORS
-- =====================================================

CREATE TABLE IF NOT EXISTS doctors (
    doctor_id INT AUTO_INCREMENT PRIMARY KEY,

    registration_number VARCHAR(100) NOT NULL UNIQUE,

    doctor_name VARCHAR(150) NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =====================================================
-- TABLE 2: PATIENTS
-- =====================================================

CREATE TABLE IF NOT EXISTS patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,

    patient_name VARCHAR(150) NOT NULL,

    contact VARCHAR(20),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =====================================================
-- TABLE 3: PRESCRIPTIONS
-- =====================================================

CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id INT AUTO_INCREMENT PRIMARY KEY,

    doctor_id INT NOT NULL,

    patient_id INT NOT NULL,

    prescription_date DATE NOT NULL,

    status ENUM(
        'ACTIVE',
        'PARTIALLY_FULFILLED',
        'COMPLETED',
        'EXPIRED',
        'CANCELLED'
    ) NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_prescription_doctor
        FOREIGN KEY (doctor_id)
        REFERENCES doctors(doctor_id),

    CONSTRAINT fk_prescription_patient
        FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id),

    INDEX idx_prescription_patient_date (
        patient_id,
        prescription_date
    )
);


-- =====================================================
-- TABLE 4: PRESCRIPTION LINES
-- =====================================================

CREATE TABLE IF NOT EXISTS prescription_lines (
    prescription_line_id INT AUTO_INCREMENT PRIMARY KEY,

    prescription_id INT NOT NULL,

    drug_id INT NOT NULL,

    dose_per_day DECIMAL(10,3) NOT NULL,

    days_supply INT UNSIGNED NOT NULL,

    required_units INT UNSIGNED NOT NULL,

    dispensed_quantity INT UNSIGNED NOT NULL DEFAULT 0,

    pending_quantity INT UNSIGNED NOT NULL DEFAULT 0,

    no_substitution BOOLEAN NOT NULL DEFAULT FALSE,

    refill_count INT UNSIGNED NOT NULL DEFAULT 0,

    pending_until DATETIME(6),

    status ENUM(
        'NEW',
        'PARTIALLY_FILLED',
        'PENDING',
        'DISPENSED',
        'REJECTED'
    ) NOT NULL DEFAULT 'NEW',

    CONSTRAINT fk_line_prescription
        FOREIGN KEY (prescription_id)
        REFERENCES prescriptions(prescription_id),

    CONSTRAINT fk_line_drug
        FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id),

    CONSTRAINT chk_line_dose
        CHECK (dose_per_day > 0),

    CONSTRAINT chk_line_days
        CHECK (days_supply > 0),

    CONSTRAINT chk_line_quantity
        CHECK (required_units > 0),

    CONSTRAINT chk_line_dispensed
        CHECK (dispensed_quantity <= required_units),

    CONSTRAINT chk_line_pending
        CHECK (
            pending_quantity <=
            required_units - dispensed_quantity
        ),

    INDEX idx_prescription_lines (
        prescription_id,
        drug_id
    )
);


-- =====================================================
-- TABLE 5: DISPENSES
-- One record represents a dispensing transaction.
-- =====================================================

CREATE TABLE IF NOT EXISTS dispenses (
    dispense_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    prescription_id INT NOT NULL,

    dispensed_at DATETIME(6) NOT NULL
        DEFAULT CURRENT_TIMESTAMP(6),

    status ENUM(
        'PARTIAL',
        'COMPLETED'
    ) NOT NULL,

    CONSTRAINT fk_dispense_prescription
        FOREIGN KEY (prescription_id)
        REFERENCES prescriptions(prescription_id),

    INDEX idx_dispense_prescription_date (
        prescription_id,
        dispensed_at
    )
);


-- =====================================================
-- TABLE 6: DISPENSE LINES
-- One prescription line may be fulfilled from
-- multiple batches.
-- =====================================================

CREATE TABLE IF NOT EXISTS dispense_lines (
    dispense_line_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    dispense_id BIGINT NOT NULL,

    prescription_line_id INT NOT NULL,

    drug_id INT NOT NULL,

    batch_id INT NOT NULL,

    quantity INT UNSIGNED NOT NULL,

    days_supply_dispensed DECIMAL(10,3) NOT NULL,

    is_substituted BOOLEAN NOT NULL DEFAULT FALSE,

    prescribed_brand VARCHAR(150) NOT NULL,

    dispensed_brand VARCHAR(150) NOT NULL,

    dispensed_at DATETIME(6) NOT NULL
        DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_dispense_line_header
        FOREIGN KEY (dispense_id)
        REFERENCES dispenses(dispense_id),

    CONSTRAINT fk_dispense_line_prescription
        FOREIGN KEY (prescription_line_id)
        REFERENCES prescription_lines(prescription_line_id),

    CONSTRAINT fk_dispense_line_drug
        FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id),

    CONSTRAINT fk_dispense_line_batch
        FOREIGN KEY (batch_id)
        REFERENCES batches(batch_id),

    CONSTRAINT chk_dispense_quantity
        CHECK (quantity > 0),

    INDEX idx_dispense_line_prescription (
        prescription_line_id
    ),

    INDEX idx_dispense_line_batch (
        batch_id
    )
);

-- =====================================================
-- END OF DISPENSING SCHEMA
-- =====================================================
