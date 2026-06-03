-- ============================================================
-- Bayan BOE Database Schema
-- Charset : utf8mb4  (full Arabic + Unicode support)
-- Collation: utf8mb4_unicode_ci
-- ============================================================

CREATE DATABASE IF NOT EXISTS bayan
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE bayan;
-- ============================================================
-- TABLE 1: boe_header
-- One row per BOE declaration file
-- Primary Key: dec_no + pdf_filename
-- ============================================================
CREATE TABLE IF NOT EXISTS boe_header (

    -- Primary key components
    dec_no                      VARCHAR(50)     NOT NULL COMMENT 'Field 1 - Declaration Number',
    pdf_filename                VARCHAR(512)    NOT NULL COMMENT 'Source PDF filename (unique per file)',

    -- Declaration info
    dec_date_hijri_2            VARCHAR(20)     DEFAULT NULL COMMENT 'Field 2A - Declaration Date Hijri',
    dec_date_gregorian_2        VARCHAR(20)     DEFAULT NULL COMMENT 'Field 2B - Declaration Date Gregorian',
    dec_type_3                  VARCHAR(255)    DEFAULT NULL COMMENT 'Field 3 - Declaration Type',
    port_type_4                 VARCHAR(100)    DEFAULT NULL COMMENT 'Field 4 - Port Type (air/sea/land)',

    -- Delivery & parties
    delivery_order_no_5         VARCHAR(255)    DEFAULT NULL COMMENT 'Field 5 - Delivery Order No',
    importer_exporter_6         VARCHAR(512)    DEFAULT NULL COMMENT 'Field 6 - Importer/Exporter Name',
    net_weight_7b               DECIMAL(12,3)   DEFAULT NULL COMMENT 'Field 7B - Net Weight',
    unload_date_7a              VARCHAR(20)     DEFAULT NULL COMMENT 'Field 7A - Unload Date',
    carrier_captain_driver_8    VARCHAR(512)    DEFAULT NULL COMMENT 'Field 8 - Carrier/Captain/Driver',
    intercessor_co_9            VARCHAR(512)    DEFAULT NULL COMMENT 'Field 9 - Intercessor Company',
    gross_weight_10             DECIMAL(12,3)   DEFAULT NULL COMMENT 'Field 10 - Gross Weight',
    carrier_name_11             VARCHAR(512)    DEFAULT NULL COMMENT 'Field 11 - Carrier Name',
    
    -- Registration & tax
    commercial_reg_no_12        VARCHAR(100)    DEFAULT NULL COMMENT 'Field 12 - Commercial Registration No',
    tin_no_12a                  VARCHAR(100)    DEFAULT NULL COMMENT 'Field 12A - Tax Identification No',

    -- Shipment details
    measurement_13              VARCHAR(100)    DEFAULT NULL COMMENT 'Field 13 - Measurement Unit',
    voyage_flight_no_14         VARCHAR(100)    DEFAULT NULL COMMENT 'Field 14 - Voyage/Flight No',
    exported_to_15              VARCHAR(255)    DEFAULT NULL COMMENT 'Field 15 - Exported To',
    packages_16                 DECIMAL(10,2)   DEFAULT NULL COMMENT 'Field 16 - No. of Packages',
    awb_no_17a                  VARCHAR(100)    DEFAULT NULL COMMENT 'Field 17A - AWB Number',
    manifest_no_17b             VARCHAR(100)    DEFAULT NULL COMMENT 'Field 17B - Manifest Number',
    port_of_loading_18          VARCHAR(255)    DEFAULT NULL COMMENT 'Field 18 - Port of Loading',
    marks_numbers_19            VARCHAR(255)    DEFAULT NULL COMMENT 'Field 19 - Marks & Numbers',
    port_of_discharge_20        VARCHAR(255)    DEFAULT NULL COMMENT 'Field 20 - Port of Discharge',
    destination_21              VARCHAR(255)    DEFAULT NULL COMMENT 'Field 21 - Destination',

    -- Agents & codes
    clearing_agent_38           VARCHAR(512)    DEFAULT NULL COMMENT 'Field 38 - Clearing Agent',
    licence_no_39               VARCHAR(255)    DEFAULT NULL COMMENT 'Field 39 - Licence No',
    unified_customs_code_43     VARCHAR(100)    DEFAULT NULL COMMENT 'Field 43 - Unified Customs Code',
    gcc_aeo_code_44             VARCHAR(100)    DEFAULT NULL COMMENT 'Field 44 - GCC AEO Code',
    other_remarks_45            TEXT            DEFAULT NULL COMMENT 'Field 45 - Other Remarks',
    exit_port_46                VARCHAR(255)    DEFAULT NULL COMMENT 'Field 46 - Exit Port',

    -- Duties & fees
    total_duty_48               DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 48 - Total Customs Duty',
    vat_48a                     DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 48A - VAT',
    excise_tax_48b              DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 48B - Excise Tax',
    anti_dumping_48c            DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 48C - Anti Dumping Duty',
    handling_49                 DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 49 - Handling Charges',
    other_charges_50            DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 50 - Other Charges',
    definite_51                 DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 51 - Definite Total',
    insured_52                  DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 52 - Insured Amount',

    -- Payment info
    payment_method_53           VARCHAR(255)    DEFAULT NULL COMMENT 'Field 53 - Payment Method',
    payment_no_54               VARCHAR(100)    DEFAULT NULL COMMENT 'Field 54 - Payment No',
    payment_date_55             VARCHAR(50)     DEFAULT NULL COMMENT 'Field 55 - Payment Date',
    payment_bank_56             VARCHAR(255)    DEFAULT NULL COMMENT 'Field 56 - Payment Bank',
    receipt_no_57               VARCHAR(100)    DEFAULT NULL COMMENT 'Field 57 - Receipt No',
    receipt_date_58             VARCHAR(50)     DEFAULT NULL COMMENT 'Field 58 - Receipt Date',
    receipt_bank_59             VARCHAR(255)    DEFAULT NULL COMMENT 'Field 59 - Receipt Bank',

    -- Audit
    created_at                  DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at                  DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (dec_no, pdf_filename)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='BOE Header Records';


-- ============================================================
-- TABLE 2: boe_line_items
-- One row per line item per declaration
-- Primary Key: dec_no + pdf_filename + item_no
-- Foreign Key → boe_header
-- ============================================================
CREATE TABLE IF NOT EXISTS boe_line_items (

    -- Primary key components
    dec_no                              VARCHAR(50)     NOT NULL COMMENT 'Declaration Number (FK → boe_header)',
    pdf_filename                        VARCHAR(512)    NOT NULL COMMENT 'Source PDF filename (FK → boe_header)',
    item_no                             TINYINT UNSIGNED NOT NULL COMMENT 'Line item number (1–99)',

    -- Tariff & description
    hs_code_22                          VARCHAR(20)     DEFAULT NULL COMMENT 'Field 22 - HS Tariff Code',
    goods_description_23                TEXT            DEFAULT NULL COMMENT 'Field 23 - Goods Description (Arabic)',
    origin_24                           VARCHAR(5)      DEFAULT NULL COMMENT 'Field 24 - Country of Origin (ISO code)',

    -- Value
    foreign_value_25                    DECIMAL(15,2)   DEFAULT NULL COMMENT 'Field 25 - Foreign Currency Value',
    currency_type_26                    VARCHAR(10)     DEFAULT NULL COMMENT 'Field 26 - Currency Type',
    currency_value_27                   DECIMAL(12,6)   DEFAULT NULL COMMENT 'Field 27 - Currency Exchange Rate',
    cif_local_value_28                  DECIMAL(15,2)   DEFAULT NULL COMMENT 'Field 28 - CIF Local Value (SAR)',

    -- Duty
    d_rate_29                           DECIMAL(7,4)    DEFAULT NULL COMMENT 'Field 29 - Duty Rate (e.g. 0.05 = 5%)',
    income_type_30                      VARCHAR(100)    DEFAULT NULL COMMENT 'Field 30 - Income Type (exempt/definite)',
    total_duty_31                       DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 31 - Total Duty Amount',

    -- Package & weight
    pkg_qty_32                          DECIMAL(10,2)   DEFAULT NULL COMMENT 'Field 32 - Package Quantity',
    pkg_type_33                         VARCHAR(100)    DEFAULT NULL COMMENT 'Field 33 - Package Type',
    item_qty_34                         DECIMAL(10,2)   DEFAULT NULL COMMENT 'Field 34 - Item Quantity',
    item_unit_35                        VARCHAR(100)    DEFAULT NULL COMMENT 'Field 35 - Item Unit',
    net_weight_36                       DECIMAL(12,3)   DEFAULT NULL COMMENT 'Field 36 - Net Weight',
    gross_weight_37                     DECIMAL(12,3)   DEFAULT NULL COMMENT 'Field 37 - Gross Weight',
    aip_no_37a                          VARCHAR(100)    DEFAULT NULL COMMENT 'Field 37A - AIP No',
    aip_duty_37b                        DECIMAL(12,2)   DEFAULT NULL COMMENT 'Field 37B - AIP Duty',

    -- Customs restrictions
    customs_restrictions_agency_40      VARCHAR(255)    DEFAULT NULL COMMENT 'Field 40 - Customs Restriction Agency',
    customs_release_ref_41              VARCHAR(255)    DEFAULT NULL COMMENT 'Field 41 - Customs Release Reference',

    -- Audit
    created_at                          DATETIME        DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (dec_no, pdf_filename, item_no),

    CONSTRAINT fk_line_items_header
        FOREIGN KEY (dec_no, pdf_filename)
        REFERENCES boe_header (dec_no, pdf_filename)
        ON DELETE CASCADE
        ON UPDATE CASCADE

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='BOE Line Item Records';
