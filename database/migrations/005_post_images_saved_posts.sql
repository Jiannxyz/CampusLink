-- Post image gallery + saved posts bookmarks.
-- Edit USE line to match your database name.

SET NAMES utf8mb4;
USE CCCS105;

CREATE TABLE IF NOT EXISTS post_images (
    image_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    post_id BIGINT UNSIGNED NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    sort_order INT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_post_images_post
        FOREIGN KEY (post_id)
        REFERENCES posts (post_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_post_images_post (post_id, sort_order)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_saved_posts (
    user_id BIGINT UNSIGNED NOT NULL,
    post_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, post_id),
    CONSTRAINT fk_user_saved_posts_user
        FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_user_saved_posts_post
        FOREIGN KEY (post_id)
        REFERENCES posts (post_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_user_saved_posts_user (user_id),
    INDEX idx_user_saved_posts_post (post_id)
) ENGINE=InnoDB;
