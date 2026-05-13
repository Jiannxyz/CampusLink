import math
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from utils.auth_helpers import enforce_admin_access
from utils.db import db_cursor
from utils.event_validation import parse_event_datetime, validate_event_form

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_ROLES = frozenset(("student", "staff", "admin"))
ALLOWED_ACCOUNT_STATUS = frozenset(("pending", "active", "suspended", "deactivated"))


@admin_bp.before_request
def _require_admin_role():
    """Admin blueprint middleware: only users with role admin may access these routes."""
    return enforce_admin_access()


def _int_page(raw):
    try:
        p = int(raw or 1)
        return p if p >= 1 else 1
    except (TypeError, ValueError):
        return 1


def _now():
    return datetime.now()


@admin_bp.route("/dashboard")
def dashboard():
    overview = {}
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
        else:
            _, cur = pair
            cur.execute(
                "SELECT COUNT(*) AS c FROM users WHERE account_status = 'active'"
            )
            overview["active_users"] = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM users")
            overview["total_users"] = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM posts")
            overview["total_posts"] = int(cur.fetchone()["c"])
            cur.execute(
                "SELECT COUNT(*) AS c FROM events WHERE event_status = 'draft'"
            )
            overview["draft_events"] = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM schools WHERE status = 'active'")
            overview["active_schools"] = int(cur.fetchone()["c"])
    return render_template("admin/dashboard.html", overview=overview)


@admin_bp.route("/users")
def users_list():
    page = _int_page(request.args.get("page"))
    per = current_app.config.get("ADMIN_MODERATION_PER_PAGE", 20)
    offset = (page - 1) * per
    rows = []
    total = 0
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
        else:
            conn, cur = pair
            cur.execute("SELECT COUNT(*) AS c FROM users")
            total = int(cur.fetchone()["c"])
            cur.execute(
                """
                SELECT
                    u.user_id,
                    u.username,
                    u.email,
                    u.first_name,
                    u.last_name,
                    u.role,
                    u.account_status,
                    u.school_id,
                    s.name AS school_name
                FROM users u
                INNER JOIN schools s ON s.school_id = u.school_id
                ORDER BY u.user_id ASC
                LIMIT %s OFFSET %s
                """,
                (per, offset),
            )
            rows = cur.fetchall()
    total_pages = max(1, math.ceil(total / per)) if total else 1
    if page > total_pages:
        return redirect(url_for("admin.users_list", page=total_pages))
    return render_template(
        "admin/users_list.html",
        users=rows,
        page=page,
        total_pages=total_pages,
        total_users=total,
    )


def _fetch_user_admin(cur, user_id):
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
            s.name AS school_name
        FROM users u
        INNER JOIN schools s ON s.school_id = u.school_id
        WHERE u.user_id = %s
        """,
        (user_id,),
    )
    return cur.fetchone()


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET"])
def user_edit(user_id):
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("admin.users_list"))
        _, cur = pair
        row = _fetch_user_admin(cur, user_id)
    if not row:
        flash("User not found.", "warning")
        return redirect(url_for("admin.users_list"))
    return render_template("admin/user_edit.html", user_row=row)


@admin_bp.route("/users/<int:user_id>/update", methods=["POST"])
def user_update(user_id):
    role = (request.form.get("role") or "").strip()
    account_status = (request.form.get("account_status") or "").strip()
    if role not in ALLOWED_ROLES:
        flash("Invalid role.", "danger")
        return redirect(url_for("admin.user_edit", user_id=user_id))
    if account_status not in ALLOWED_ACCOUNT_STATUS:
        flash("Invalid account status.", "danger")
        return redirect(url_for("admin.user_edit", user_id=user_id))

    actor_id = int(g.current_user["user_id"])

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("admin.user_edit", user_id=user_id))
        conn, cur = pair
        row = _fetch_user_admin(cur, user_id)
        if not row:
            flash("User not found.", "warning")
            return redirect(url_for("admin.users_list"))

        if user_id == actor_id and account_status != "active":
            flash("You cannot change your own account to a non-active status here.", "danger")
            return redirect(url_for("admin.user_edit", user_id=user_id))

        was_admin_active = (
            row.get("role") == "admin" and row.get("account_status") == "active"
        )
        will_admin_active = role == "admin" and account_status == "active"
        if was_admin_active and not will_admin_active:
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM users
                WHERE role = 'admin' AND account_status = 'active'
                """
            )
            admin_count = int(cur.fetchone()["c"])
            if admin_count < 2:
                flash(
                    "Cannot remove the last active administrator. Promote another admin first.",
                    "danger",
                )
                return redirect(url_for("admin.user_edit", user_id=user_id))

        cur.execute(
            """
            UPDATE users SET role = %s, account_status = %s
            WHERE user_id = %s
            """,
            (role, account_status, user_id),
        )
        conn.commit()

    flash("User updated.", "success")
    return redirect(url_for("admin.user_edit", user_id=user_id))


@admin_bp.route("/posts")
def posts_moderation():
    page = _int_page(request.args.get("page"))
    per = current_app.config.get("ADMIN_MODERATION_PER_PAGE", 20)
    offset = (page - 1) * per
    rows = []
    total = 0
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
        else:
            conn, cur = pair
            cur.execute("SELECT COUNT(*) AS c FROM posts")
            total = int(cur.fetchone()["c"])
            cur.execute(
                """
                SELECT
                    p.post_id,
                    p.title,
                    p.category,
                    p.privacy,
                    p.created_at,
                    LEFT(p.content, 160) AS excerpt,
                    u.username,
                    s.name AS school_name
                FROM posts p
                INNER JOIN users u ON u.user_id = p.user_id
                INNER JOIN schools s ON s.school_id = p.school_id
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (per, offset),
            )
            rows = cur.fetchall()
    total_pages = max(1, math.ceil(total / per)) if total else 1
    if page > total_pages:
        return redirect(url_for("admin.posts_moderation", page=total_pages))
    return render_template(
        "admin/posts_moderation.html",
        posts=rows,
        page=page,
        total_pages=total_pages,
        total_posts=total,
    )


@admin_bp.route("/events/pending")
def events_pending():
    rows = []
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
        else:
            _, cur = pair
            cur.execute(
                """
                SELECT
                    e.event_id,
                    e.title,
                    e.starts_at,
                    e.visibility,
                    e.school_id,
                    s.name AS school_name,
                    u.username AS organizer_username
                FROM events e
                INNER JOIN schools s ON s.school_id = e.school_id
                INNER JOIN users u ON u.user_id = e.created_by_user_id
                WHERE e.event_status = 'draft'
                ORDER BY e.created_at DESC
                """
            )
            rows = cur.fetchall()
    return render_template("admin/events_pending.html", events=rows)


@admin_bp.route("/events/<int:event_id>/approve", methods=["POST"])
def event_approve(event_id):
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("admin.events_pending"))
        conn, cur = pair
        cur.execute(
            """
            SELECT
                e.event_id,
                e.school_id,
                e.organization_id,
                e.title,
                e.description,
                e.location,
                e.starts_at,
                e.ends_at,
                e.visibility,
                e.event_status,
                e.capacity
            FROM events e
            WHERE e.event_id = %s
            """,
            (event_id,),
        )
        row = cur.fetchone()

    if not row or row.get("event_status") != "draft":
        flash("That draft event was not found or is no longer a draft.", "warning")
        return redirect(url_for("admin.events_pending"))

    title = (row.get("title") or "").strip()
    description = (row.get("description") or "") or ""
    venue = (row.get("location") or "") or ""
    starts = row.get("starts_at")
    if starts is not None and hasattr(starts, "replace") and getattr(starts, "tzinfo", None):
        starts = starts.replace(tzinfo=None)
    ends = row.get("ends_at")
    if ends is not None and hasattr(ends, "replace") and getattr(ends, "tzinfo", None):
        ends = ends.replace(tzinfo=None)
    visibility = (row.get("visibility") or "school_only").strip()
    cap = row.get("capacity")
    if cap is not None:
        try:
            cap = int(cap)
        except (TypeError, ValueError):
            cap = None

    now = _now()
    errors = validate_event_form(
        title,
        description,
        venue,
        starts,
        ends,
        visibility,
        "published",
        cap,
        now,
        require_future_start_if_published=False,
    )
    if errors:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("admin.events_pending"))

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("admin.events_pending"))
        conn, cur = pair
        cur.execute(
            """
            UPDATE events
            SET event_status = 'published'
            WHERE event_id = %s AND event_status = 'draft'
            """,
            (event_id,),
        )
        if cur.rowcount == 0:
            flash("Event could not be approved (it may have changed).", "warning")
        else:
            conn.commit()
            flash("Event published.", "success")

    return redirect(url_for("admin.events_pending"))
