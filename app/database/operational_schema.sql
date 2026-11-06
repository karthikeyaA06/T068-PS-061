-- PS-061 operational workflows: run AFTER schema.sql, dispensing_schema.sql,
-- billing_schema.sql and compliance_schema.sql.
USE pharmacy_inventory;

-- OTC sales reuse the common dispense/bill tables. A NULL prescription_id
-- identifies an OTC sale; a NULL prescription_line_id identifies its line.
ALTER TABLE dispenses
    MODIFY prescription_id INT NULL,
    MODIFY patient_id INT NULL;

ALTER TABLE dispense_lines
    MODIFY prescription_line_id INT NULL;

CREATE TABLE IF NOT EXISTS customer_returns (
    customer_return_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    bill_line_id BIGINT NOT NULL,
    batch_id INT NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    refund_amount DECIMAL(14,2) NOT NULL,
    unopened BOOLEAN NOT NULL,
    returned_at DATETIME(6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customer_return_bill_line
        FOREIGN KEY (bill_line_id) REFERENCES bill_lines(bill_line_id),
    CONSTRAINT fk_customer_return_batch
        FOREIGN KEY (batch_id) REFERENCES batches(batch_id),
    CONSTRAINT chk_customer_return_qty CHECK (quantity > 0),
    CONSTRAINT chk_customer_return_refund CHECK (refund_amount >= 0),
    INDEX idx_customer_return_bill_line (bill_line_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS supplier_returns (
    supplier_return_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id INT NOT NULL,
    supplier_id INT NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    reason VARCHAR(255) NOT NULL,
    status ENUM('PENDING','COMPLETED','CANCELLED') NOT NULL DEFAULT 'PENDING',
    requested_at DATETIME(6) NOT NULL,
    completed_at DATETIME(6) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_supplier_return_batch
        FOREIGN KEY (batch_id) REFERENCES batches(batch_id),
    CONSTRAINT fk_supplier_return_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    CONSTRAINT chk_supplier_return_qty CHECK (quantity > 0),
    INDEX idx_supplier_return_pending (batch_id, status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS batch_recalls (
    recall_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id INT NOT NULL UNIQUE,
    reason VARCHAR(500) NOT NULL,
    recalled_at DATETIME(6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_batch_recall_batch
        FOREIGN KEY (batch_id) REFERENCES batches(batch_id),
    INDEX idx_batch_recall_timestamp (recalled_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS batch_writeoffs (
    writeoff_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id INT NOT NULL UNIQUE,
    quantity INT UNSIGNED NOT NULL,
    purchase_price_per_unit DECIMAL(12,2) NOT NULL,
    writeoff_value DECIMAL(14,2) NOT NULL,
    business_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_writeoff_batch
        FOREIGN KEY (batch_id) REFERENCES batches(batch_id),
    CONSTRAINT chk_writeoff_qty CHECK (quantity > 0),
    INDEX idx_writeoff_date (business_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reorder_suggestions (
    reorder_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    drug_id INT NOT NULL,
    business_date DATE NOT NULL,
    valid_stock INT UNSIGNED NOT NULL,
    minimum_stock INT UNSIGNED NOT NULL,
    reorder_quantity INT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reorder_drug
        FOREIGN KEY (drug_id) REFERENCES drugs(drug_id),
    CONSTRAINT uq_reorder_drug_day UNIQUE (drug_id, business_date),
    INDEX idx_reorder_date (business_date)
) ENGINE=InnoDB;
