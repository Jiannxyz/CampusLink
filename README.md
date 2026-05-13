# CampusLink

Beginner-friendly Flask project with modular architecture, MySQL support, and Bootstrap 5 templates.

## Project Structure

- `docs/diagrams/` - project diagrams (`erd.png`, `rm.png`)
- `database/` - SQL schema and seed data
- `src/` - Flask application source code

## Database

1. Create the schema (defaults to database `campuslink_db` in `database/schema.sql`):
   - `mysql -u root -p < database/schema.sql`
2. Load sample data:
   - `mysql -u root -p < database/initial_data.sql`
3. Set `MYSQL_DATABASE` in `.env` to match the database name you use.

Seed accounts (after `initial_data.sql`):

- Admin: username `admin_alice`, password `AdminCampus123!`
- Student: username `bob_student` (or `carol_student`, `dave_student`), password `CampusLink123!`

## School management (admin)

Admins can manage schools at **Schools** in the navbar (`/schools`): list, detail, create, edit, and delete.

Deleting a school is blocked while **users** still reference it (`users.school_id` is `RESTRICT`). Other tables that reference schools may also prevent delete; in that case MySQL returns an error and a flash message is shown.

If your database was created from an older `schema.sql` without `campus`, `province`, `description`, or `logo_path`, run:

- `mysql -u root -p < database/migrations/001_schools_extended_fields.sql`  
  (edit the `USE …` line in that file to match your database name first.)

If your database predates **post** columns `title`, `image_path`, and `category`, run:

- `mysql -u root -p < database/migrations/002_posts_social_fields.sql`  
  (edit the `USE …` line first.)

## Campus feed & posts

- **Feed** (`/feed`): paginated posts with optional **school filter**. Guests see **public** posts only; signed-in users also see **school-only** posts for their school and their own **private** / **followers-only** posts (followers-only is author-only until follow-based sharing is implemented).
- **Create / edit / delete** (`/posts/new`, `/posts/<id>/edit`, POST delete): requires sign-in; **authors** and **admins** can edit or delete.
- Configure page size with `POSTS_PER_PAGE` in `.env` (default 10).

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env file:
   - `cp .env.example .env`
4. Update database settings and `SECRET_KEY` in `.env`.
5. Run the app:
   - `python3 src/app.py`

## Authentication

- Registration creates **student** accounts (`role = student`, `account_status = active`).
- Passwords are hashed with `werkzeug.security` (PBKDF2 by default).
- Sessions use Flask’s signed cookie; configure `SESSION_COOKIE_SECURE` for HTTPS in production.
- Protected routes use `@login_required`; admin pages use `@admin_required` (see `src/routes/admin.py`).
