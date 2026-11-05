
-- =====================================================
-- PS-061: PHARMACY INVENTORY MANAGEMENT SYSTEM
-- WEEK 2: DATABASE SCHEMA - FOUNDATION
-- Database: MySQL 8.0
-- =====================================================

CREATE DATABASE IF NOT EXISTS pharmacy_inventory;

USE pharmacy_inventory;


-- =====================================================
-- TABLE 1: SUBSTITUTION GROUPS
-- Groups brands with the same molecule, strength and form
-- =====================================================

CREATE TABLE IF NOT EXISTS substitution_groups (
    group_id INT AUTO_INCREMENT PRIMARY KEY,

    molecule VARCHAR(150) NOT NULL,

    strength VARCHAR(80) NOT NULL,

    dosage_form VARCHAR(80) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_substitution_group
        UNIQUE (molecule, strength, dosage_form)
);


-- =====================================================
-- TABLE 2: DRUGS
-- Stores registered drug master information
-- =====================================================

CREATE TABLE IF NOT EXISTS drugs (
    drug_id INT AUTO_INCREMENT PRIMARY KEY,

    group_id INT NOT NULL,

    brand_name VARCHAR(150) NOT NULL,

    schedule ENUM('NONE', 'H', 'H1', 'X')
        NOT NULL DEFAULT 'NONE',

    mrp DECIMAL(12,2) NOT NULL,

    gst_rate DECIMAL(4,2) NOT NULL,

    pack_size INT UNSIGNED NOT NULL,

    min_stock INT UNSIGNED NOT NULL DEFAULT 0,

    sells_full_packs BOOLEAN NOT NULL DEFAULT FALSE,

    controlled_substance BOOLEAN NOT NULL DEFAULT FALSE,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_drug_group
        FOREIGN KEY (group_id)
        REFERENCES substitution_groups(group_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT uq_group_brand
        UNIQUE (group_id, brand_name),

    CONSTRAINT chk_drug_mrp
        CHECK (mrp > 0),

    CONSTRAINT chk_drug_gst
        CHECK (gst_rate IN (5.00, 12.00)),

    CONSTRAINT chk_drug_pack_size
        CHECK (pack_size > 0)
);


-- =====================================================
-- TABLE 3: SUPPLIERS
-- Stores pharmacy supplier information
-- =====================================================

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,

    supplier_name VARCHAR(200) NOT NULL,

    contact_person VARCHAR(150),

    phone VARCHAR(20),

    email VARCHAR(150),

    address TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =====================================================
-- TABLE 4: BATCHES
-- Stores batch-wise inventory information
-- =====================================================

CREATE TABLE IF NOT EXISTS batches (
    batch_id INT AUTO_INCREMENT PRIMARY KEY,

    drug_id INT NOT NULL,

    supplier_id INT NOT NULL,

    batch_number VARCHAR(100) NOT NULL,

    -- Store the first day of the expiry month.
    -- Python will calculate the last calendar day.

    expiry_month_start DATE NOT NULL,

    received_at DATETIME(6) NOT NULL
        DEFAULT CURRENT_TIMESTAMP(6),

    received_quantity INT UNSIGNED NOT NULL,

    available_quantity INT UNSIGNED NOT NULL,

    -- Proposed representation: purchase price per base unit.
    -- Confirm the unit basis against the supplied sample data.

    purchase_price DECIMAL(12,2) NOT NULL,

    status ENUM(
        'ACTIVE',
        'FROZEN',
        'DEPLETED',
        'RETURNED',
        'EXPIRED',
        'WRITTEN_OFF'
    ) NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_batch_drug
        FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_batch_supplier
        FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT uq_drug_batch
        UNIQUE (drug_id, batch_number),

    CONSTRAINT chk_batch_expiry_month
        CHECK (DAY(expiry_month_start) = 1),

    CONSTRAINT chk_batch_received_quantity
        CHECK (received_quantity > 0),

    CONSTRAINT chk_batch_available_quantity
        CHECK (available_quantity <= received_quantity),

    CONSTRAINT chk_batch_purchase_price
        CHECK (purchase_price >= 0),

    INDEX idx_batch_fefo (
        drug_id,
        status,
        expiry_month_start,
        received_at,
        batch_number
    )
);

-- =====================================================
-- END OF FOUNDATION SCHEMA
-- =====================================================
