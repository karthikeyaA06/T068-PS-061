USE pharmacy_inventory;

CREATE TABLE IF NOT EXISTS h1_register_entries (
    h1_entry_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dispense_line_id BIGINT NOT NULL UNIQUE,
    patient_name VARCHAR(255) NOT NULL,
    doctor_registration_number VARCHAR(100) NOT NULL,
    dispense_date DATETIME(6) NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_h1_register_dispense_line
        FOREIGN KEY (dispense_line_id)
        REFERENCES dispense_lines(dispense_line_id),
    CONSTRAINT chk_h1_register_quantity
        CHECK (quantity > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS x_register_entries (
    x_entry_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dispense_line_id BIGINT NOT NULL UNIQUE,
    patient_name VARCHAR(255) NOT NULL,
    doctor_registration_number VARCHAR(100) NOT NULL,
    batch_number VARCHAR(100) NOT NULL,
    dispense_date DATETIME(6) NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_x_register_dispense_line
        FOREIGN KEY (dispense_line_id)
        REFERENCES dispense_lines(dispense_line_id),
    CONSTRAINT chk_x_register_quantity
        CHECK (quantity > 0)
) ENGINE=InnoDB;
