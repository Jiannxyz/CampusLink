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
