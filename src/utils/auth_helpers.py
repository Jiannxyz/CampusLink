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
            SELECT
                u.user_id,
                u.school_id,
                u.username,
                u.email,
                u.first_name,
                u.last_name,
                u.role,
                u.account_status,
                u.bio,
                u.profile_image_url,
                u.cover_image_path,
                u.last_seen_at,
                u.social_link_website,
                u.social_link_twitter,
                u.social_link_linkedin,
                u.created_at,
                s.name AS school_name
            FROM users u
            INNER JOIN schools s ON s.school_id = u.school_id
            WHERE u.user_id = %s
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
