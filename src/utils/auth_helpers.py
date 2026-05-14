from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from utils.db import db_cursor


def fetch_user_by_id(user_id):
    if not user_id:
        return None
    with db_cursor() as pair:
        if pair is None:
            return None
        conn, cur = pair
        cur.execute(
            """
            SELECT user_id, school_id, username, email,
                   first_name, last_name, role, account_status,
                   bio, profile_image_url, cover_image_path,
                   last_seen_at,
                   social_link_website, social_link_twitter, social_link_linkedin,
                   created_at
            FROM users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        return cur.fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.current_user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def enforce_admin_access():
    """
    Role-based gate for admin-only areas. Returns None if the request may proceed,
    otherwise a redirect response (login or home).
    """
    user = getattr(g, "current_user", None)
    if user is None:
        flash("Please log in to continue.", "warning")
        return redirect(url_for("auth.login", next=request.path))
    if user.get("role") != "admin":
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("main.home"))
    return None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        denied = enforce_admin_access()
        if denied is not None:
            return denied
        return view(*args, **kwargs)

    return wrapped


def safe_next_path(raw_next):
    if raw_next and raw_next.startswith("/") and not raw_next.startswith("//"):
        return raw_next
    return None


def login_user(user_id, remember=False):
    session.clear()
    session["user_id"] = user_id
    session.permanent = bool(remember)
