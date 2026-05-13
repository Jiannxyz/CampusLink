import math

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

from utils.auth_helpers import login_required
from utils.db import db_cursor
from utils.post_validation import validate_post_form

posts_bp = Blueprint("posts", __name__)


def _normalize_image_path(raw):
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    if s.startswith("/static/"):
        return s[len("/static/") :]
    return s


def _can_manage_post(post_row):
    user = g.current_user
    if not user or not post_row:
        return False
    if user.get("role") == "admin":
        return True
    return int(post_row["user_id"]) == int(user["user_id"])


def _visibility_sql_and_params(viewer):
    if viewer is None:
        return "p.privacy = %s", ["public"]
    uid = int(viewer["user_id"])
    sid = int(viewer["school_id"])
    sql = """(
            p.privacy = 'public'
            OR (p.privacy = 'school_only' AND p.school_id = %s)
            OR (p.privacy IN ('private', 'followers_only') AND p.user_id = %s)
            OR p.user_id = %s
        )"""
    return sql, [sid, uid, uid]


def _schools_for_filter():
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


def _parse_school_filter(raw):
    if raw is None or raw == "":
        return None
    try:
        sid = int(raw)
    except (TypeError, ValueError):
        return None
    with db_cursor() as pair:
        if pair is None:
            return None
        conn, cur = pair
        cur.execute(
            "SELECT school_id FROM schools WHERE school_id = %s AND status = 'active'",
            (sid,),
        )
        row = cur.fetchone()
        return sid if row else None


def _feed_url(page, school_id=None):
    args = {}
    if page and page > 1:
        args["page"] = page
    if school_id:
        args["school_id"] = school_id
    return url_for("posts.feed", **args)


@posts_bp.route("/feed")
def feed():
    per_page = current_app.config.get("POSTS_PER_PAGE", 10)
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    school_filter = _parse_school_filter(request.args.get("school_id"))
    vis_sql, vis_params = _visibility_sql_and_params(getattr(g, "current_user", None))

    where_parts = [vis_sql]
    params = list(vis_params)
    if school_filter is not None:
        where_parts.append("p.school_id = %s")
        params.append(school_filter)

    where_clause = " AND ".join(where_parts)

    count_sql = f"SELECT COUNT(*) AS c FROM posts p WHERE {where_clause}"
    list_sql = f"""
        SELECT
            p.post_id,
            p.title,
            p.content,
            p.image_path,
            p.category,
            p.privacy,
            p.created_at,
            p.updated_at,
            p.is_edited,
            p.user_id,
            p.school_id,
            u.username,
            u.first_name,
            u.last_name,
            s.name AS school_name
        FROM posts p
        INNER JOIN users u ON u.user_id = p.user_id
        INNER JOIN schools s ON s.school_id = p.school_id
        WHERE {where_clause}
        ORDER BY p.created_at DESC
        LIMIT %s OFFSET %s
    """

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return render_template(
                "feed/index.html",
                posts=[],
                schools_filter=_schools_for_filter(),
                school_filter=school_filter,
                pagination=None,
            )

        conn, cur = pair
        cur.execute(count_sql, tuple(params))
        total = int(cur.fetchone()["c"])
        pages = max(1, math.ceil(total / per_page)) if total else 1
        page = min(page, pages)
        offset = (page - 1) * per_page

        cur.execute(list_sql, tuple(params + [per_page, offset]))
        rows = cur.fetchall()

    pagination = {
        "page": page,
        "pages": pages,
        "total": total,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if page < pages else None,
    }

    return render_template(
        "feed/index.html",
        posts=rows,
        schools_filter=_schools_for_filter(),
        school_filter=school_filter,
        pagination=pagination,
        feed_url=_feed_url,
    )


def _empty_post_values():
    return {
        "title": "",
        "content": "",
        "image_path": "",
        "category": "general",
        "privacy": "school_only",
    }


def _values_from_form():
    return {
        "title": (request.form.get("title") or "").strip(),
        "content": (request.form.get("content") or "").strip(),
        "image_path": (request.form.get("image_path") or "").strip(),
        "category": (request.form.get("category") or "general").strip(),
        "privacy": (request.form.get("privacy") or "school_only").strip(),
    }


def _values_from_post_row(row):
    return {
        "title": row.get("title") or "",
        "content": row.get("content") or "",
        "image_path": row.get("image_path") or "",
        "category": row.get("category") or "general",
        "privacy": row.get("privacy") or "school_only",
    }


@posts_bp.route("/posts/new", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        vals = _values_from_form()
        img = _normalize_image_path(vals["image_path"])
        errors = validate_post_form(
            vals["title"],
            vals["content"],
            img or "",
            vals["category"],
            vals["privacy"],
        )
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("posts/create.html", values=vals)

        post_type = "image" if img else "text"
        uid = int(g.current_user["user_id"])
        sid = int(g.current_user["school_id"])

        with db_cursor() as pair:
            if pair is None:
                flash("Cannot reach the database.", "danger")
                return render_template("posts/create.html", values=vals)
            conn, cur = pair
            cur.execute(
                """
                INSERT INTO posts (
                    title, user_id, school_id, organization_id,
                    content, image_path, category, privacy, post_type, is_edited
                )
                VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, 0)
                """,
                (
                    vals["title"],
                    uid,
                    sid,
                    vals["content"],
                    img,
                    vals["category"],
                    vals["privacy"],
                    post_type,
                ),
            )
            new_id = cur.lastrowid
            conn.commit()

        flash("Post published.", "success")
        return redirect(url_for("posts.feed"))

    return render_template("posts/create.html", values=_empty_post_values())


def _fetch_post(post_id):
    with db_cursor() as pair:
        if pair is None:
            return None
        conn, cur = pair
        cur.execute(
            """
            SELECT
                p.*,
                u.username,
                u.first_name,
                u.last_name,
                s.name AS school_name
            FROM posts p
            INNER JOIN users u ON u.user_id = p.user_id
            INNER JOIN schools s ON s.school_id = p.school_id
            WHERE p.post_id = %s
            """,
            (post_id,),
        )
        return cur.fetchone()


@posts_bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = _fetch_post(post_id)
    if not post:
        flash("Post not found.", "warning")
        return redirect(url_for("posts.feed"))

    if not _can_manage_post(post):
        flash("You cannot edit this post.", "danger")
        return redirect(url_for("posts.feed"))

    if request.method == "POST":
        vals = _values_from_form()
        img = _normalize_image_path(vals["image_path"])
        errors = validate_post_form(
            vals["title"],
            vals["content"],
            img or "",
            vals["category"],
            vals["privacy"],
        )
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("posts/edit.html", post=post, values=vals)

        post_type = "image" if img else "text"

        with db_cursor() as pair:
            if pair is None:
                flash("Cannot reach the database.", "danger")
                return render_template("posts/edit.html", post=post, values=vals)
            conn, cur = pair
            cur.execute(
                """
                UPDATE posts SET
                    title = %s,
                    content = %s,
                    image_path = %s,
                    category = %s,
                    privacy = %s,
                    post_type = %s,
                    is_edited = 1
                WHERE post_id = %s
                """,
                (
                    vals["title"],
                    vals["content"],
                    img,
                    vals["category"],
                    vals["privacy"],
                    post_type,
                    post_id,
                ),
            )
            conn.commit()

        flash("Post updated.", "success")
        return redirect(url_for("posts.feed"))

    return render_template(
        "posts/edit.html",
        post=post,
        values=_values_from_post_row(post),
    )


@posts_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = _fetch_post(post_id)
    if not post:
        flash("Post not found.", "warning")
        return redirect(url_for("posts.feed"))

    if not _can_manage_post(post):
        flash("You cannot delete this post.", "danger")
        return redirect(url_for("posts.feed"))

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("posts.feed"))
        conn, cur = pair
        cur.execute("DELETE FROM posts WHERE post_id = %s", (post_id,))
        conn.commit()

    flash("Post deleted.", "info")
    return redirect(url_for("posts.feed"))
