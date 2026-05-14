-- Add title, image_path, category, and indexes to posts when missing.
-- Safe to run multiple times. No stored procedures.
-- Requires MariaDB 10.3.3+ for ADD COLUMN IF NOT EXISTS.
-- Edit USE to match your database name.

USE CCCS105;

ALTER TABLE posts
    ADD COLUMN IF NOT EXISTS title VARCHAR(200) NOT NULL DEFAULT 'Post' AFTER post_id,
    ADD COLUMN IF NOT EXISTS image_path VARCHAR(500) NULL AFTER content,
    ADD COLUMN IF NOT EXISTS category ENUM(
        'general',
        'academic',
        'events',
        'clubs',
        'questions',
        'marketplace'
    ) NOT NULL DEFAULT 'general' AFTER image_path;

-- Indexes (only if missing; avoids duplicate key name errors on upgraded DBs)
SET @db := DATABASE();

SET @has_cat := (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = @db AND table_name = 'posts' AND index_name = 'idx_posts_category'
);
SET @sql_cat := IF(@has_cat = 0, 'ALTER TABLE posts ADD INDEX idx_posts_category (category)', 'SELECT 1');
PREPARE stmt_cat FROM @sql_cat;
EXECUTE stmt_cat;
DEALLOCATE PREPARE stmt_cat;

SET @has_title := (
    SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = @db AND table_name = 'posts' AND index_name = 'idx_posts_title'
);
SET @sql_title := IF(@has_title = 0, 'ALTER TABLE posts ADD INDEX idx_posts_title (title(80))', 'SELECT 1');
PREPARE stmt_title FROM @sql_title;
EXECUTE stmt_title;
DEALLOCATE PREPARE stmt_title;
