-- Add campus, province, description, and logo_path to schools (run once on existing DBs).
-- Apply once if your database was created before these columns existed.
-- Change the database name below to match your environment (e.g. CCCS105).

USE CCCS105;

ALTER TABLE schools
    ADD COLUMN campus VARCHAR(150) NULL AFTER name,
    ADD COLUMN province VARCHAR(100) NULL AFTER city,
    ADD COLUMN description TEXT NULL AFTER country,
    ADD COLUMN logo_path VARCHAR(500) NULL AFTER description;
