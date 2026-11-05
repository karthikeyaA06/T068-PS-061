
-- =====================================================
-- PS-061: BILLING DATABASE SCHEMA
-- Business Rule: BR-06
-- =====================================================

USE pharmacy_inventory;

-- BILL HEADER
CREATE TABLE IF NOT EXISTS bills (
    bill_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    dispense_id BIGINT NOT NULL UNIQUE,

    customer_id INT NOT NULL,

    subtotal DECIMAL(14,2) NOT NULL,

    discount_total DECIMAL(14,2) NOT NULL,

    gst_total DECIMAL(14,2) NOT NULL,

    total_before_rounding DECIMAL(14,2) NOT NULL,

    rounding_adjustment DECIMAL(14,2) NOT NULL,

    grand_total DECIMAL(14,2) NOT NULL,

    bill_date DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT fk_bill_dispense
        FOREIGN KEY (dispense_id)
        REFERENCES dispenses(dispense_id),

    CONSTRAINT fk_bill_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);


-- BILL LINE DETAILS
CREATE TABLE IF NOT EXISTS bill_lines (
    bill_line_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    bill_id BIGINT NOT NULL,

    dispense_line_id BIGINT NOT NULL UNIQUE,

    drug_id INT NOT NULL,

    batch_id INT NOT NULL,

    quantity INT UNSIGNED NOT NULL,

    mrp_inclusive DECIMAL(14,2) NOT NULL,

    discount_rate DECIMAL(5,2) NOT NULL,

    discount_amount DECIMAL(14,2) NOT NULL,

    gst_rate DECIMAL(5,2) NOT NULL,

    taxable_value DECIMAL(14,2) NOT NULL,

    gst_amount DECIMAL(14,2) NOT NULL,

    line_total DECIMAL(14,2) NOT NULL,

    CONSTRAINT fk_bill_line_bill
        FOREIGN KEY (bill_id)
        REFERENCES bills(bill_id),

    CONSTRAINT fk_bill_line_dispense
        FOREIGN KEY (dispense_line_id)
        REFERENCES dispense_lines(dispense_line_id),

    CONSTRAINT fk_bill_line_drug
        FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id),

    CONSTRAINT fk_bill_line_batch
        FOREIGN KEY (batch_id)
        REFERENCES batches(batch_id),

    CONSTRAINT chk_bill_line_quantity
        CHECK (quantity > 0),

    INDEX idx_bill_lines_bill (bill_id)
);

-- =====================================================
-- END OF BILLING SCHEMA
-- =====================================================
