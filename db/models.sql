-- ============================================================
-- Bayan BOE Database Schema for SQL Server
-- Unicode stored as NVARCHAR (native SQL Server Unicode)
-- ============================================================

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'bayan')
BEGIN
    CREATE DATABASE bayan;
END
GO

USE bayan;
GO

-- ============================================================
-- TABLE 1: boe_header
-- ============================================================
IF OBJECT_ID('boe_header', 'U') IS NOT NULL DROP TABLE boe_header;
GO

CREATE TABLE boe_header (

    -- Primary key
    dec_no                      NVARCHAR(50)    NOT NULL,
    pdf_filename                NVARCHAR(512)   NOT NULL,

    -- Declaration info
    dec_date_hijri_2            NVARCHAR(MAX)    NULL,
    dec_date_gregorian_2        NVARCHAR(MAX)    NULL,
    dec_type_3                  NVARCHAR(MAX)   NULL,
    port_type_4                 NVARCHAR(MAX)   NULL,

    -- Delivery & parties
    delivery_order_no_5         NVARCHAR(MAX)   NULL,
    importer_exporter_6         NVARCHAR(MAX)   NULL,
    unload_date_7a              NVARCHAR(MAX)    NULL,
    net_weight_7b               DECIMAL(12,3)   NULL,
    carrier_captain_driver_8    NVARCHAR(MAX)   NULL,
    intercessor_co_9            NVARCHAR(MAX)   NULL,
    gross_weight_10             DECIMAL(12,3)   NULL,
    carrier_name_11             NVARCHAR(MAX)   NULL,

    -- Registration & tax
    commercial_reg_no_12        NVARCHAR(MAX)   NULL,
    tin_no_12a                  NVARCHAR(MAX)   NULL,

    -- Shipment details
    measurement_13              NVARCHAR(MAX)   NULL,
    voyage_flight_no_14         NVARCHAR(MAX)   NULL,
    exported_to_15              NVARCHAR(MAX)   NULL,
    packages_16                 DECIMAL(10,2)   NULL,
    awb_no_17a                  NVARCHAR(MAX)   NULL,
    manifest_no_17b             NVARCHAR(MAX)   NULL,
    port_of_loading_18          NVARCHAR(MAX)   NULL,
    marks_numbers_19            NVARCHAR(MAX)   NULL,
    port_of_discharge_20        NVARCHAR(MAX)   NULL,
    destination_21              NVARCHAR(MAX)   NULL,

    -- Agents & codes
    clearing_agent_38           NVARCHAR(MAX)   NULL,
    licence_no_39               NVARCHAR(MAX)   NULL,
    unified_customs_code_43     NVARCHAR(MAX)   NULL,
    gcc_aeo_code_44             NVARCHAR(MAX)   NULL,
    other_remarks_45            NVARCHAR(MAX)   NULL,
    exit_port_46                NVARCHAR(MAX)   NULL,

    -- Duties & fees
    total_duty_48               DECIMAL(12,2)   NULL,
    vat_48a                     DECIMAL(12,2)   NULL,
    excise_tax_48b              DECIMAL(12,2)   NULL,
    anti_dumping_48c            DECIMAL(12,2)   NULL,
    handling_49                 DECIMAL(12,2)   NULL,
    other_charges_50            DECIMAL(12,2)   NULL,
    definite_51                 DECIMAL(12,2)   NULL,
    insured_52                  DECIMAL(12,2)   NULL,

    -- Payment info
    payment_method_53           NVARCHAR(MAX)   NULL,
    payment_no_54               NVARCHAR(MAX)   NULL,
    payment_date_55             NVARCHAR(MAX)    NULL,
    payment_bank_56             NVARCHAR(MAX)   NULL,
    receipt_no_57               NVARCHAR(MAX)   NULL,
    receipt_date_58             NVARCHAR(MAX)    NULL,
    receipt_bank_59             NVARCHAR(MAX)   NULL,

    -- Audit
    created_at                  DATETIME        DEFAULT GETDATE(),
    updated_at                  DATETIME        DEFAULT GETDATE(),

    PRIMARY KEY (dec_no, pdf_filename)
);
GO

-- ============================================================
-- TABLE 2: boe_line_items
-- ============================================================
IF OBJECT_ID('boe_line_items', 'U') IS NOT NULL DROP TABLE boe_line_items;
GO

CREATE TABLE boe_line_items (

    -- Primary key
    dec_no                              NVARCHAR(50)        NOT NULL,
    pdf_filename                        NVARCHAR(512)       NOT NULL,
    item_no                             TINYINT             NOT NULL,

    -- Tariff & description
    hs_code_22                          NVARCHAR(MAX)        NULL,
    goods_description_23                NVARCHAR(MAX)       NULL,
    origin_24                           NVARCHAR(MAX)         NULL,

    -- Value
    foreign_value_25                    DECIMAL(15,2)       NULL,
    currency_type_26                    NVARCHAR(MAX)        NULL,
    currency_value_27                   DECIMAL(12,6)       NULL,
    cif_local_value_28                  DECIMAL(15,2)       NULL,

    -- Duty
    d_rate_29                           DECIMAL(7,4)        NULL,
    income_type_30                      NVARCHAR(MAX)       NULL,
    total_duty_31                       DECIMAL(12,2)       NULL,

    -- Package & weight
    pkg_qty_32                          DECIMAL(10,2)       NULL,
    pkg_type_33                         NVARCHAR(MAX)       NULL,
    item_qty_34                         DECIMAL(10,2)       NULL,
    item_unit_35                        NVARCHAR(MAX)       NULL,
    net_weight_36                       DECIMAL(12,3)       NULL,
    gross_weight_37                     DECIMAL(12,3)       NULL,
    aip_no_37a                          NVARCHAR(MAX)       NULL,
    aip_duty_37b                        DECIMAL(12,2)       NULL,

    -- Customs restrictions
    customs_restrictions_agency_40      NVARCHAR(MAX)       NULL,
    customs_release_ref_41              NVARCHAR(MAX)       NULL,
    exemption_code_42                   NVARCHAR(MAX)        NULL,

    -- Audit
    created_at                          DATETIME            DEFAULT GETDATE(),
    updated_at                          DATETIME            DEFAULT GETDATE(), --NEW

    PRIMARY KEY (dec_no, pdf_filename, item_no),

    CONSTRAINT fk_line_items_header
        FOREIGN KEY (dec_no, pdf_filename)
        REFERENCES boe_header (dec_no, pdf_filename)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
GO



-- ============================================================
-- TABLE 3: logs
-- ============================================================
CREATE TABLE app_logs (
    id INT IDENTITY(1,1) NOT NULL,
    [timestamp] DATETIME2(0) NOT NULL,    
    [log_level] NVARCHAR(10) NOT NULL,  
    [logger_name] NVARCHAR(100) NOT NULL, 
    [message] NVARCHAR(MAX) NOT NULL,    
    [created_at] DATETIME2(0) NOT NULL DEFAULT GETDATE(), -- DB tracking timestamp
    
    CONSTRAINT PK_app_logs PRIMARY KEY CLUSTERED (id ASC)
);

-- Highly recommended non-clustered indexes for fast querying of log data
CREATE NONCLUSTERED INDEX IX_app_logs_timestamp 
ON app_logs ([timestamp] DESC);

CREATE NONCLUSTERED INDEX IX_app_logs_log_level 
ON app_logs ([log_level]);