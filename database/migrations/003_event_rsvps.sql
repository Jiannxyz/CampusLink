-- RSVP / attendance table for events (run once on existing databases).
USE CCCS105;

CREATE TABLE IF NOT EXISTS event_rsvps (
    event_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    status ENUM('going', 'waitlist', 'cancelled') NOT NULL DEFAULT 'going',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id, user_id),
    CONSTRAINT fk_event_rsvps_event
        FOREIGN KEY (event_id)
        REFERENCES events (event_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_event_rsvps_user
        FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_event_rsvps_user (user_id),
    INDEX idx_event_rsvps_status (event_id, status)
) ENGINE=InnoDB;
