-- User profile extensions, social links, presence, saved events.
-- Edit USE line to match your database name.

SET NAMES utf8mb4;
USE CCCS105;

ALTER TABLE users
    ADD COLUMN cover_image_path VARCHAR(500) NULL DEFAULT NULL AFTER profile_image_url,
    ADD COLUMN last_seen_at TIMESTAMP NULL DEFAULT NULL AFTER last_login_at,
    ADD COLUMN social_link_website VARCHAR(300) NULL DEFAULT NULL AFTER bio,
    ADD COLUMN social_link_twitter VARCHAR(200) NULL DEFAULT NULL AFTER social_link_website,
    ADD COLUMN social_link_linkedin VARCHAR(300) NULL DEFAULT NULL AFTER social_link_twitter;

CREATE TABLE IF NOT EXISTS user_saved_events (
    user_id BIGINT UNSIGNED NOT NULL,
    event_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, event_id),
    CONSTRAINT fk_user_saved_events_user
        FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_user_saved_events_event
        FOREIGN KEY (event_id)
        REFERENCES events (event_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_user_saved_events_user (user_id),
    INDEX idx_user_saved_events_event (event_id)
) ENGINE=InnoDB;
