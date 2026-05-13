-- CampusLink sample seed data (matches database/schema.sql)
-- Run after schema.sql on a fresh database.
--
-- Demo passwords (werkzeug pbkdf2:sha256 hashes below):
--   Admin user:  AdminCampus123!
--   All others:  CampusLink123!

SET NAMES utf8mb4;
USE CCCS105;

SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM reactions;
DELETE FROM comments;
DELETE FROM posts;
DELETE FROM follows;
DELETE FROM events;
DELETE FROM organizations;
DELETE FROM users;
DELETE FROM schools;

ALTER TABLE schools AUTO_INCREMENT = 1;
ALTER TABLE users AUTO_INCREMENT = 1;
ALTER TABLE organizations AUTO_INCREMENT = 1;
ALTER TABLE posts AUTO_INCREMENT = 1;
ALTER TABLE comments AUTO_INCREMENT = 1;
ALTER TABLE reactions AUTO_INCREMENT = 1;
ALTER TABLE events AUTO_INCREMENT = 1;

SET FOREIGN_KEY_CHECKS = 1;

-- Password hashes generated with:
-- werkzeug.security.generate_password_hash(..., method='pbkdf2:sha256')

INSERT INTO schools (school_code, name, email_domain, city, country, status) VALUES
('STATE-U', 'State University', 'stateu.edu', 'Springfield', 'USA', 'active'),
('TECH-COLLEGE', 'Tech College', 'techcollege.edu', 'Metro City', 'USA', 'active');

INSERT INTO users (
    school_id, username, email, password_hash,
    first_name, last_name, role, account_status, bio
) VALUES
(
    1,
    'admin_alice',
    'alice.admin@stateu.edu',
    'pbkdf2:sha256:1000000$d7X0K9vdfJlCVa9c$0392c89ead07761f653528abea97af20155cfd31e1f05376df2bb9ef11a7ebd4',
    'Alice',
    'Admin',
    'admin',
    'active',
    'Campus administrator.'
),
(
    1,
    'bob_student',
    'bob@stateu.edu',
    'pbkdf2:sha256:1000000$P864HgoCX0B23xp3$bb1165416f5823a6631deaaf3e64e12b1e410332abf4f775261d998a39a2735a',
    'Bob',
    'Student',
    'student',
    'active',
    'Computer science major.'
),
(
    1,
    'carol_student',
    'carol@stateu.edu',
    'pbkdf2:sha256:1000000$P864HgoCX0B23xp3$bb1165416f5823a6631deaaf3e64e12b1e410332abf4f775261d998a39a2735a',
    'Carol',
    'Student',
    'student',
    'active',
    NULL
),
(
    2,
    'dave_student',
    'dave@techcollege.edu',
    'pbkdf2:sha256:1000000$P864HgoCX0B23xp3$bb1165416f5823a6631deaaf3e64e12b1e410332abf4f775261d998a39a2735a',
    'Dave',
    'Student',
    'student',
    'active',
    'Design club member.'
);

INSERT INTO organizations (
    school_id, created_by_user_id, name, slug, description, visibility, status
) VALUES
(1, 1, 'Computer Science Club', 'cs-club', 'Weekly meetups and hackathons.', 'school_only', 'active'),
(1, 2, 'Photography Society', 'photo-soc', 'Campus photo walks and exhibitions.', 'public', 'active');

INSERT INTO posts (
    user_id, school_id, organization_id, content, privacy, post_type, is_edited
) VALUES
(2, 1, 1, 'Welcome to the CS Club feed! First hackathon is next month.', 'school_only', 'text', 0),
(3, 1, NULL, 'Anyone taking Advanced Databases this semester?', 'school_only', 'text', 0),
(4, 2, NULL, 'Sharing photos from the spring showcase—great work everyone!', 'public', 'text', 0);

INSERT INTO comments (post_id, user_id, parent_comment_id, content, is_edited) VALUES
(1, 3, NULL, 'Count me in for the hackathon!', 0),
(2, 2, NULL, 'Yes—Prof. Lee''s section here.', 0),
(2, 1, 2, 'Office hours moved to Thursday this week.', 0);

INSERT INTO reactions (user_id, target_type, target_id, reaction_type) VALUES
(2, 'post', 1, 'like'),
(3, 'post', 1, 'love'),
(1, 'comment', 1, 'like'),
(4, 'post', 3, 'wow');

INSERT INTO events (
    school_id, organization_id, created_by_user_id,
    title, description, location, starts_at, ends_at,
    visibility, event_status, capacity
) VALUES
(
    1,
    1,
    1,
    'Fall Hackathon 2026',
    '24-hour build sprint. Teams of up to four.',
    'Engineering Building, Lab 201',
    '2026-09-15 09:00:00',
    '2026-09-16 09:00:00',
    'school_only',
    'published',
    80
),
(
    2,
    NULL,
    4,
    'Design Portfolio Review',
    'Bring your portfolio for peer feedback.',
    'Arts Wing, Room 105',
    '2026-06-01 14:00:00',
    '2026-06-01 17:00:00',
    'public',
    'published',
    25
);

INSERT INTO follows (follower_user_id, following_user_id, follow_status) VALUES
(2, 3, 'accepted'),
(3, 4, 'accepted'),
(4, 2, 'accepted');
