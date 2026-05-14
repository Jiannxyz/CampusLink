-- Add campus, province, description, and logo_path to schools when missing.
-- Safe to run multiple times (no stored procedures — avoids mysql.proc / mysql_upgrade issues).
-- Requires MariaDB 10.3.3+ or MySQL 8.0.29+ for ADD COLUMN IF NOT EXISTS.
-- Set database name below for your environment.

USE CCCS105;

ALTER TABLE schools
    ADD COLUMN IF NOT EXISTS campus VARCHAR(150) NULL AFTER name,
    ADD COLUMN IF NOT EXISTS province VARCHAR(100) NULL AFTER city,
    ADD COLUMN IF NOT EXISTS description TEXT NULL AFTER country,
    ADD COLUMN IF NOT EXISTS logo_path VARCHAR(500) NULL AFTER description;
