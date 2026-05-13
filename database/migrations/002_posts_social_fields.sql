-- Add title, image_path, and category to posts (run once on existing databases).
-- Edit USE to match your database name.

USE CCCS105;

ALTER TABLE posts
    ADD COLUMN title VARCHAR(200) NOT NULL DEFAULT 'Post' AFTER post_id,
    ADD COLUMN image_path VARCHAR(500) NULL AFTER content,
    ADD COLUMN category ENUM(
        'general',
        'academic',
        'events',
        'clubs',
        'questions',
        'marketplace'
    ) NOT NULL DEFAULT 'general' AFTER image_path,
    ADD INDEX idx_posts_category (category),
    ADD INDEX idx_posts_title (title(80));
