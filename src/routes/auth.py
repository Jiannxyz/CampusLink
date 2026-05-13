from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from utils.auth_helpers import login_user, safe_next_path
from utils.db import db_cursor
from utils.validation import (
    validate_email,
    validate_name,
    validate_password,
    validate_username,
)

auth_bp = Blueprint("auth", __name__)


def _active_schools():
    with db_cursor() as pair:
        if pair is None:
            return []
        conn, cur = pair
        cur.execute(
            """
            SELECT school_id, name
            FROM schools
            WHERE status = 'active'
            ORDER BY name
            """
        )
        return cur.fetchall()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    schools = _active_schools()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        school_raw = request.form.get("school_id", "")

        errors = [
            validate_username(username),
            validate_email(email),
            validate_password(password),
            validate_name(first_name, last_name),
        ]
        err = next((e for e in errors if e), None)
        if err:
            flash(err, "danger")
            return render_template("auth/register.html", schools=schools)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", schools=schools)

        try:
            school_id = int(school_raw)
        except (TypeError, ValueError):
            flash("Choose a valid school.", "danger")
            return render_template("auth/register.html", schools=schools)

        password_hash = generate_password_hash(password)

        try:
            with db_cursor() as pair:
                if pair is None:
                    flash("Cannot reach the database. Try again later.", "danger")
                    return render_template("auth/register.html", schools=schools)

                conn, cur = pair
                cur.execute(
                    """
                    SELECT 1 FROM schools
                    WHERE school_id = %s AND status = 'active'
                    """,
                    (school_id,),
                )
                if cur.fetchone() is None:
                    flash("Choose a valid school.", "danger")
                    return render_template("auth/register.html", schools=schools)

                cur.execute(
                    """
                    INSERT INTO users (
                        school_id, username, email, password_hash,
                        first_name, last_name, role, account_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'student', 'active')
                    """,
                    (
                        school_id,
                        username,
                        email,
                        password_hash,
                        first_name,
                        last_name,
                    ),
                )
                new_id = cur.lastrowid
                conn.commit()

            login_user(new_id, remember=False)
            flash("Welcome to CampusLink — your account is ready.", "success")
            return redirect(url_for("main.dashboard"))

        except IntegrityError:
            flash("That username or email is already registered.", "danger")
            return render_template("auth/register.html", schools=schools)

    if not schools:
        flash(
            "No schools are available yet. Ask an administrator to load the database.",
            "warning",
        )
    return render_template("auth/register.html", schools=schools)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not identifier or not password:
            flash("Enter your username or email and password.", "danger")
            return render_template("auth/login.html")

        with db_cursor() as pair:
            if pair is None:
                flash("Cannot reach the database. Try again later.", "danger")
                return render_template("auth/login.html")

            conn, cur = pair
            cur.execute(
                """
                SELECT user_id, password_hash, account_status
                FROM users
                WHERE username = %s OR email = %s
                LIMIT 1
                """,
                (identifier, identifier),
            )
            row = cur.fetchone()

        if row is None or not check_password_hash(row["password_hash"], password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html")

        if row["account_status"] != "active":
            flash("This account is not active. Contact support.", "warning")
            return render_template("auth/login.html")

        with db_cursor() as pair:
            if pair is None:
                flash("Cannot reach the database. Try again later.", "danger")
                return render_template("auth/login.html")
            conn, cur = pair
            cur.execute(
                """
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (row["user_id"],),
            )
            conn.commit()

        login_user(row["user_id"], remember=remember)
        flash("You are signed in.", "success")

        next_raw = request.form.get("next") or request.args.get("next")
        next_path = safe_next_path(next_raw)
        return redirect(next_path or url_for("main.dashboard"))

    return render_template("auth/login.html", next=request.args.get("next"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))
