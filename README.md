# CampusLink

Beginner-friendly Flask project with modular architecture, MySQL support, and Bootstrap 5 templates.

## Project Structure

- `docs/diagrams/` - project diagrams (`erd.png`, `rm.png`)
- `database/` - SQL schema and seed data
- `src/` - Flask application source code

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy env file:
   - `cp .env.example .env`
4. Update database settings in `.env`.
5. Run the app:
   - `python3 src/app.py`
