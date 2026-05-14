
-- -----------------------------
-- 1) schools
-- -----------------------------
CREATE TABLE IF NOT EXISTS schools (
    school_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_code VARCHAR(30) NOT NULL,
    name VARCHAR(150) NOT NULL,
    campus VARCHAR(150) NULL,
    email_domain VARCHAR(120) NOT NULL,
    city VARCHAR(100) NULL,
    province VARCHAR(100) NULL,
    country VARCHAR(100) NULL,
    description TEXT NULL,
    logo_path VARCHAR(500) NULL,
    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_schools_school_code UNIQUE (school_code),
    CONSTRAINT uq_schools_email_domain UNIQUE (email_domain),
    INDEX idx_schools_name (name)
) ENGINE=InnoDB;

-- -----------------------------
-- 2) users
-- Supports authentication + school-based communities
-- -----------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id BIGINT UNSIGNED NOT NULL,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    role ENUM('student', 'staff', 'admin') NOT NULL DEFAULT 'student',
    account_status ENUM('pending', 'active', 'suspended', 'deactivated') NOT NULL DEFAULT 'pending',
    bio VARCHAR(300) NULL,
    profile_image_url VARCHAR(255) NULL,
    cover_image_path VARCHAR(500) NULL,
    last_login_at TIMESTAMP NULL,
    last_seen_at TIMESTAMP NULL,
    social_link_website VARCHAR(300) NULL,
    social_link_twitter VARCHAR(200) NULL,
    social_link_linkedin VARCHAR(300) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT fk_users_school
        FOREIGN KEY (school_id)
        REFERENCES schools (school_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_users_school (school_id),
    INDEX idx_users_name (last_name, first_name),
    INDEX idx_users_status (account_status)
) ENGINE=InnoDB;

-- -----------------------------
-- 3) organizations
-- Student/staff groups under a school
-- -----------------------------
CREATE TABLE IF NOT EXISTS organizations (
    organization_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id BIGINT UNSIGNED NOT NULL,
    created_by_user_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(160) NOT NULL,
    description TEXT NULL,
    visibility ENUM('public', 'school_only', 'private') NOT NULL DEFAULT 'school_only',
    status ENUM('active', 'archived') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_org_school_slug UNIQUE (school_id, slug),
    CONSTRAINT fk_org_school
        FOREIGN KEY (school_id)
        REFERENCES schools (school_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_org_creator
        FOREIGN KEY (created_by_user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_org_school (school_id),
    INDEX idx_org_creator (created_by_user_id)
) ENGINE=InnoDB;

-- -----------------------------
-- 4) posts
-- Core social content
-- -----------------------------
CREATE TABLE IF NOT EXISTS posts (
    post_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    school_id BIGINT UNSIGNED NOT NULL,
    organization_id BIGINT UNSIGNED NULL,
    content TEXT NOT NULL,
    image_path VARCHAR(500) NULL,
    category ENUM('general', 'academic', 'events', 'clubs', 'questions', 'marketplace') NOT NULL DEFAULT 'general',
    privacy ENUM('public', 'school_only', 'followers_only', 'private') NOT NULL DEFAULT 'school_only',
    post_type ENUM('text', 'image', 'announcement', 'event_share') NOT NULL DEFAULT 'text',
    is_edited TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_posts_user
        FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_posts_school
        FOREIGN KEY (school_id)
        REFERENCES schools (school_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_posts_organization
        FOREIGN KEY (organization_id)
        REFERENCES organizations (organization_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    INDEX idx_posts_user_created (user_id, created_at),
    INDEX idx_posts_school_created (school_id, created_at),
    INDEX idx_posts_org_created (organization_id, created_at),
    INDEX idx_posts_privacy (privacy),
    INDEX idx_posts_category (category),
    INDEX idx_posts_title (title(80))
) ENGINE=InnoDB;

-- -----------------------------
-- 5) comments
-- Supports threaded comments via parent_comment_id
-- -----------------------------
CREATE TABLE IF NOT EXISTS comments (
    comment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    post_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    parent_comment_id BIGINT UNSIGNED NULL,
    content TEXT NOT NULL,
    is_edited TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_comments_post
        FOREIGN KEY (post_id)
        REFERENCES posts (post_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_comments_user
        FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_comments_parent
        FOREIGN KEY (parent_comment_id)
        REFERENCES comments (comment_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_comments_post_created (post_id, created_at),
    INDEX idx_comments_user_created (user_id, created_at),
    INDEX idx_comments_parent (parent_comment_id)
) ENGINE=InnoDB;

-- -----------------------------
-- 6) reactions
-- Normalized polymorphic target through target_type + target_id
-- Unique reaction per user per target
-- -----------------------------
CREATE TABLE IF NOT EXISTS reactions (
    reaction_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    target_type ENUM('post', 'comment') NOT NULL,
    target_id BIGINT UNSIGNED NOT NULL,
    reaction_type ENUM('like', 'love', 'haha', 'wow', 'sad', 'angry') NOT NULL DEFAULT 'like',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reactions_user
        FOREIGN KEY (user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT uq_reactions_user_target UNIQUE (user_id, target_type, target_id),
    INDEX idx_reactions_target (target_type, target_id),
    INDEX idx_reactions_user (user_id),
    INDEX idx_reactions_type (reaction_type)
) ENGINE=InnoDB;

-- -----------------------------
-- 7) events
-- Event management for school communities
-- -----------------------------
CREATE TABLE IF NOT EXISTS events (
    event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id BIGINT UNSIGNED NOT NULL,
    organization_id BIGINT UNSIGNED NULL,
    created_by_user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(180) NOT NULL,
    description TEXT NULL,
    location VARCHAR(200) NULL,
    starts_at DATETIME NOT NULL,
    ends_at DATETIME NULL,
    visibility ENUM('public', 'school_only', 'organization_only') NOT NULL DEFAULT 'school_only',
    event_status ENUM('draft', 'published', 'cancelled', 'completed') NOT NULL DEFAULT 'draft',
    capacity INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_events_date_range CHECK (ends_at IS NULL OR ends_at >= starts_at),
    CONSTRAINT fk_events_school
        FOREIGN KEY (school_id)
        REFERENCES schools (school_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_events_organization
        FOREIGN KEY (organization_id)
        REFERENCES organizations (organization_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_events_creator
        FOREIGN KEY (created_by_user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_events_school_starts (school_id, starts_at),
    INDEX idx_events_org_starts (organization_id, starts_at),
    INDEX idx_events_creator (created_by_user_id),
    INDEX idx_events_status (event_status)
) ENGINE=InnoDB;

-- -----------------------------
-- 7b) event RSVPs (attendance)
-- -----------------------------
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

-- -----------------------------
-- 7c) user saved events (bookmarks)
-- -----------------------------
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

-- -----------------------------
-- 8) follows
-- User-to-user follow graph
-- -----------------------------
CREATE TABLE IF NOT EXISTS follows (
    follower_user_id BIGINT UNSIGNED NOT NULL,
    following_user_id BIGINT UNSIGNED NOT NULL,
    follow_status ENUM('pending', 'accepted', 'blocked') NOT NULL DEFAULT 'accepted',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (follower_user_id, following_user_id),
    CONSTRAINT chk_follows_not_self CHECK (follower_user_id <> following_user_id),
    CONSTRAINT fk_follows_follower
        FOREIGN KEY (follower_user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_follows_following
        FOREIGN KEY (following_user_id)
        REFERENCES users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_follows_following (following_user_id),
    INDEX idx_follows_status (follow_status)
) ENGINE=InnoDB;
