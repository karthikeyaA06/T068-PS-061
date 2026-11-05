
USE pharmacy_inventory;

CREATE TABLE IF NOT EXISTS h1_register_entries (
    entry_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dispense_line_id BIGINT NOT NULL UNIQUE,
    patient_name VARCHAR(150) NOT NULL,
    doctor_registration_number VARCHAR(100) NOT NULL,
    dispense_date DATETIME(6) NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    FOREIGN KEY (dispense_line_id)
        REFERENCES dispense_lines(dispense_line_id),
    CHECK (quantity > 0)
);

CREATE TABLE IF NOT EXISTS x_register_entries (
    entry_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dispense_line_id BIGINT NOT NULL UNIQUE,
    patient_name VARCHAR(150) NOT NULL,
    doctor_registration_number VARCHAR(100) NOT NULL,
    batch_number VARCHAR(100) NOT NULL,
    dispense_date DATETIME(6) NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    FOREIGN KEY (dispense_line_id)
        REFERENCES dispense_lines(dispense_line_id),
    CHECK (quantity > 0)
);
