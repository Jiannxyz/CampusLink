import os
from datetime import datetime, timedelta

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
from werkzeug.security import check_password_hash, generate_password_hash

from utils.auth_helpers import login_required, safe_next_path
from utils.db import db_cursor
from utils.profile_upload import delete_old_upload, save_user_image
from utils.profile_validation import validate_profile_form

profiles_bp = Blueprint("profiles", __name__)

ONLINE_WINDOW = timedelta(minutes=5)


def is_user_online(last_seen_at):
    if not last_seen_at:
        return False
    ts = last_seen_at
    if hasattr(ts, "replace") and getattr(ts, "tzinfo", None):
        ts = ts.replace(tzinfo=None)
    return datetime.now() - ts <= ONLINE_WINDOW


def _static_dir():
    return os.path.join(current_app.root_path, "static")


def fetch_profile_row(cur, username):
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
        WHERE u.username = %s
        """,
        (username,),
    )
    return cur.fetchone()


def fetch_profile_row_by_id(cur, user_id):
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


def fetch_profile_stats(cur, user_id):
    out = {"posts": 0, "followers": 0, "following": 0, "events_joined": 0}
    cur.execute(
        "SELECT COUNT(*) AS c FROM posts WHERE user_id = %s",
        (user_id,),
    )
    out["posts"] = int(cur.fetchone()["c"])
    cur.execute(
        """
        SELECT COUNT(*) AS c FROM follows
        WHERE following_user_id = %s AND follow_status = 'accepted'
        """,
        (user_id,),
    )
    out["followers"] = int(cur.fetchone()["c"])
    cur.execute(
        """
        SELECT COUNT(*) AS c FROM follows
        WHERE follower_user_id = %s AND follow_status = 'accepted'
        """,
        (user_id,),
    )
    out["following"] = int(cur.fetchone()["c"])
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS c FROM event_rsvps
            WHERE user_id = %s AND status IN ('going', 'waitlist')
            """,
            (user_id,),
        )
        out["events_joined"] = int(cur.fetchone()["c"])
    except Exception:
        out["events_joined"] = 0
    return out


def _fetch_profile_posts(cur, profile_user_id, viewer):
    is_owner = viewer and int(viewer["user_id"]) == int(profile_user_id)
    if is_owner:
        cur.execute(
            """
            SELECT post_id, title, category, privacy, created_at, LEFT(content, 220) AS excerpt
            FROM posts
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 30
            """,
            (profile_user_id,),
        )
        return cur.fetchall()
    sid = int(viewer["school_id"]) if viewer else None
    cur.execute(
        """
        SELECT post_id, title, category, privacy, created_at, LEFT(content, 220) AS excerpt
        FROM posts
        WHERE user_id = %s
          AND (
            privacy = 'public'
            OR (privacy = 'school_only' AND %s IS NOT NULL AND school_id = %s)
          )
        ORDER BY created_at DESC
        LIMIT 30
        """,
        (profile_user_id, sid, sid),
    )
    return cur.fetchall()


def _fetch_profile_events(cur, profile_user_id, viewer):
    is_owner = viewer and int(viewer["user_id"]) == int(profile_user_id)
    if is_owner:
        cur.execute(
            """
            SELECT e.event_id, e.title, e.starts_at, e.event_status, e.visibility, s.name AS school_name
            FROM events e
            INNER JOIN schools s ON s.school_id = e.school_id
            WHERE e.created_by_user_id = %s
            ORDER BY e.starts_at DESC
            LIMIT 30
            """,
            (profile_user_id,),
        )
        return cur.fetchall()
    if not viewer:
        cur.execute(
            """
            SELECT e.event_id, e.title, e.starts_at, e.event_status, e.visibility, s.name AS school_name
            FROM events e
            INNER JOIN schools s ON s.school_id = e.school_id
            WHERE e.created_by_user_id = %s
              AND e.event_status = 'published'
              AND e.visibility = 'public'
            ORDER BY e.starts_at DESC
            LIMIT 30
            """,
            (profile_user_id,),
        )
        return cur.fetchall()
    sid = int(viewer["school_id"])
    cur.execute(
        """
        SELECT e.event_id, e.title, e.starts_at, e.event_status, e.visibility, s.name AS school_name
        FROM events e
        INNER JOIN schools s ON s.school_id = e.school_id
        WHERE e.created_by_user_id = %s
          AND e.event_status = 'published'
          AND (
            e.visibility = 'public'
            OR (e.visibility IN ('school_only', 'organization_only') AND e.school_id = %s)
          )
        ORDER BY e.starts_at DESC
        LIMIT 30
        """,
        (profile_user_id, sid),
    )
    return cur.fetchall()


def _fetch_profile_orgs(cur, profile_user_id):
    cur.execute(
        """
        SELECT organization_id, name, slug, description FROM (
            SELECT organization_id, name, slug, description
            FROM organizations
            WHERE created_by_user_id = %s AND status = 'active'
            UNION
            SELECT o.organization_id, o.name, o.slug, o.description
            FROM organizations o
            INNER JOIN posts p ON p.organization_id = o.organization_id AND p.user_id = %s
            WHERE o.status = 'active'
        ) t
        ORDER BY name
        LIMIT 40
        """,
        (profile_user_id, profile_user_id),
    )
    return cur.fetchall()


def _fetch_saved_events(cur, user_id):
    cur.execute(
        """
        SELECT e.event_id, e.title, e.starts_at, e.visibility, e.event_status, s.name AS school_name
        FROM user_saved_events se
        INNER JOIN events e ON e.event_id = se.event_id
        INNER JOIN schools s ON s.school_id = e.school_id
        WHERE se.user_id = %s
        ORDER BY se.created_at DESC
        LIMIT 40
        """,
        (user_id,),
    )
    return cur.fetchall()


@profiles_bp.route("/profile")
@login_required
def profile_me():
    u = g.current_user
    return redirect(url_for("profiles.profile_by_id", user_id=int(u["user_id"])))


@profiles_bp.route("/profile/<int:user_id>")
def profile_by_id(user_id):
    tab = (request.args.get("tab") or "posts").strip().lower()
    if tab not in ("posts", "events", "organizations", "saved"):
        tab = "posts"

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("main.home"))
        _, cur = pair
        profile = fetch_profile_row_by_id(cur, user_id)
        if not profile:
            flash("Profile not found.", "warning")
            return redirect(url_for("main.home"))

        viewer = getattr(g, "current_user", None)
        is_owner = viewer and int(viewer["user_id"]) == int(profile["user_id"])

        if profile.get("account_status") != "active" and not is_owner:
            flash("This profile is not available.", "warning")
            return redirect(url_for("main.home"))

        if tab == "saved" and not is_owner:
            tab = "posts"

        stats = fetch_profile_stats(cur, int(profile["user_id"]))
        posts = _fetch_profile_posts(cur, int(profile["user_id"]), viewer)
        events = _fetch_profile_events(cur, int(profile["user_id"]), viewer)
        orgs = _fetch_profile_orgs(cur, int(profile["user_id"]))
        saved = _fetch_saved_events(cur, int(profile["user_id"])) if is_owner else []

    online = is_user_online(profile.get("last_seen_at"))

    return render_template(
        "profiles/view.html",
        profile=profile,
        stats=stats,
        tab=tab,
        posts=posts,
        events=events,
        organizations=orgs,
        saved_events=saved,
        is_owner=is_owner,
        is_online=online,
    )


@profiles_bp.route("/u/<username>")
def profile_view(username):
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("main.home"))
        _, cur = pair
        profile = fetch_profile_row(cur, username)
        if not profile:
            flash("Profile not found.", "warning")
            return redirect(url_for("main.home"))
        uid = int(profile["user_id"])
    tab = request.args.get("tab")
    if tab:
        return redirect(url_for("profiles.profile_by_id", user_id=uid, tab=tab))
    return redirect(url_for("profiles.profile_by_id", user_id=uid))


@profiles_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    uid = int(g.current_user["user_id"])
    if request.method == "POST":
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        bio = (request.form.get("bio") or "").strip() or None
        website = (request.form.get("social_link_website") or "").strip() or None
        twitter = (request.form.get("social_link_twitter") or "").strip() or None
        linkedin = (request.form.get("social_link_linkedin") or "").strip() or None
        new_password = request.form.get("new_password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        errors = validate_profile_form(
            first_name,
            last_name,
            username,
            email,
            bio,
            website,
            twitter,
            linkedin,
            new_password,
            confirm_password,
        )
        school_raw = request.form.get("school_id", "").strip()
        try:
            school_id = int(school_raw) if school_raw else int(g.current_user["school_id"])
        except (TypeError, ValueError):
            errors.append("Choose a valid school.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return redirect(url_for("profiles.profile_edit"))

        with db_cursor() as pair:
            if pair is None:
                flash("Cannot reach the database.", "danger")
                return redirect(url_for("profiles.profile_edit"))
            conn, cur = pair
            cur.execute(
                "SELECT 1 FROM schools WHERE school_id = %s AND status = 'active'",
                (school_id,),
            )
            if cur.fetchone() is None:
                flash("Invalid school.", "danger")
                return redirect(url_for("profiles.profile_edit"))

            cur.execute(
                "SELECT 1 FROM users WHERE username = %s AND user_id <> %s",
                (username, uid),
            )
            if cur.fetchone():
                flash("That username is already taken.", "danger")
                return redirect(url_for("profiles.profile_edit"))

            cur.execute(
                "SELECT 1 FROM users WHERE email = %s AND user_id <> %s",
                (email, uid),
            )
            if cur.fetchone():
                flash("That email is already in use.", "danger")
                return redirect(url_for("profiles.profile_edit"))

            cur.execute(
                """
                SELECT password_hash, profile_image_url, cover_image_path
                FROM users WHERE user_id = %s
                """,
                (uid,),
            )
            row = cur.fetchone()
            if not row:
                flash("Account not found.", "danger")
                return redirect(url_for("auth.logout"))

            current_pw = request.form.get("current_password") or ""
            if new_password:
                if not check_password_hash(row["password_hash"], current_pw):
                    flash("Current password is incorrect.", "danger")
                    return redirect(url_for("profiles.profile_edit"))

            static_dir = _static_dir()
            new_avatar = None
            new_cover = None
            try:
                pf = request.files.get("profile_photo")
                cf = request.files.get("cover_photo")
                if pf and (pf.filename or "").strip():
                    new_avatar = save_user_image(pf, uid, static_dir)
                if cf and (cf.filename or "").strip():
                    new_cover = save_user_image(cf, uid, static_dir)
            except ValueError as ex:
                flash(str(ex), "danger")
                return redirect(url_for("profiles.profile_edit"))

            profile_path = row["profile_image_url"]
            cover_path = row["cover_image_path"]
            remove_avatar = request.form.get("remove_profile_photo")
            remove_cover = request.form.get("remove_cover_photo")
            if new_avatar:
                delete_old_upload(static_dir, profile_path)
                profile_path = new_avatar
            elif remove_avatar:
                delete_old_upload(static_dir, profile_path)
                profile_path = None
            if new_cover:
                delete_old_upload(static_dir, cover_path)
                cover_path = new_cover
            elif remove_cover:
                delete_old_upload(static_dir, cover_path)
                cover_path = None

            pw_hash = row["password_hash"]
            if new_password:
                pw_hash = generate_password_hash(new_password)

            cur.execute(
                """
                UPDATE users SET
                    school_id = %s,
                    username = %s,
                    email = %s,
                    first_name = %s,
                    last_name = %s,
                    bio = %s,
                    profile_image_url = %s,
                    cover_image_path = %s,
                    social_link_website = %s,
                    social_link_twitter = %s,
                    social_link_linkedin = %s,
                    password_hash = %s
                WHERE user_id = %s
                """,
                (
                    school_id,
                    username,
                    email,
                    first_name,
                    last_name,
                    bio,
                    profile_path,
                    cover_path,
                    website,
                    twitter,
                    linkedin,
                    pw_hash,
                    uid,
                ),
            )
            conn.commit()

        flash("Profile updated.", "success")
        return redirect(url_for("profiles.profile_by_id", user_id=uid))

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("main.dashboard"))
        _, cur = pair
        cur.execute(
            """
            SELECT
                u.user_id, u.school_id, u.username, u.email,
                u.first_name, u.last_name, u.bio,
                u.profile_image_url, u.cover_image_path,
                u.social_link_website, u.social_link_twitter, u.social_link_linkedin,
                s.name AS school_name
            FROM users u
            INNER JOIN schools s ON s.school_id = u.school_id
            WHERE u.user_id = %s
            """,
            (uid,),
        )
        user_row = cur.fetchone()
        cur.execute(
            "SELECT school_id, name FROM schools WHERE status = 'active' ORDER BY name"
        )
        schools = cur.fetchall()

    return render_template(
        "profiles/edit.html",
        user_row=user_row,
        schools=schools,
    )


@profiles_bp.route("/settings")
@login_required
def settings_page():
    return render_template("settings/index.html")


@profiles_bp.route("/saved/events")
@login_required
def saved_events_page():
    uid = int(g.current_user["user_id"])
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            rows = []
        else:
            _, cur = pair
            rows = _fetch_saved_events(cur, uid)
    return render_template(
        "profiles/saved_events.html",
        events=rows,
    )


@profiles_bp.route("/saved/posts")
@login_required
def saved_posts_page():
    uid = int(g.current_user["user_id"])
    rows = []
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
        else:
            _, cur = pair
            try:
                cur.execute(
                    """
                    SELECT p.post_id, p.title, p.created_at, s.name AS school_name
                    FROM user_saved_posts us
                    INNER JOIN posts p ON p.post_id = us.post_id
                    INNER JOIN schools s ON s.school_id = p.school_id
                    WHERE us.user_id = %s
                    ORDER BY us.created_at DESC
                    LIMIT 100
                    """,
                    (uid,),
                )
                rows = cur.fetchall()
            except Exception:
                flash("Saved posts require the saved posts database table (see migration 005).", "warning")
    return render_template("profiles/saved_posts.html", posts=rows)


@profiles_bp.route("/events/<int:event_id>/save", methods=["POST"])
@login_required
def toggle_save_event(event_id):
    uid = int(g.current_user["user_id"])
    next_url = request.form.get("next") or request.referrer or url_for("events.upcoming")
    dest = safe_next_path(request.form.get("next")) or next_url
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(dest)
        conn, cur = pair
        cur.execute("SELECT 1 FROM events WHERE event_id = %s", (event_id,))
        if not cur.fetchone():
            flash("Event not found.", "warning")
            return redirect(dest)
        cur.execute(
            "SELECT 1 FROM user_saved_events WHERE user_id = %s AND event_id = %s",
            (uid, event_id),
        )
        if cur.fetchone():
            cur.execute(
                "DELETE FROM user_saved_events WHERE user_id = %s AND event_id = %s",
                (uid, event_id),
            )
            flash("Removed from saved events.", "info")
        else:
            try:
                cur.execute(
                    "INSERT INTO user_saved_events (user_id, event_id) VALUES (%s, %s)",
                    (uid, event_id),
                )
                flash("Event saved.", "success")
            except Exception:
                flash("Could not save this event (saved events may require a database migration).", "danger")
        conn.commit()
    return redirect(dest)
