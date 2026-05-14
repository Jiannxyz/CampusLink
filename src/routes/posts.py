import math
import os
from collections import defaultdict

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

from utils.auth_helpers import login_required, safe_next_path
from utils.comment_validation import validate_comment_content
from utils.db import db_cursor
from utils.post_upload import save_post_images
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


def _feed_url(page, school_id=None, compose=None):
    args = {}
    if page and page > 1:
        args["page"] = page
    if school_id:
        args["school_id"] = school_id
    if compose:
        args["compose"] = 1
    return url_for("posts.feed", **args)


def _posts_upload_dir():
    return os.path.join(current_app.root_path, "static", "uploads", "posts")


def _get_request_image_files():
    files = request.files.getlist("images")
    if not files or all(not (f and getattr(f, "filename", None)) for f in files):
        files = request.files.getlist("images[]")
    return [f for f in files if f and getattr(f, "filename", None)]


def _attach_gallery_and_saved(cur, rows, viewer):
    if not rows:
        return
    post_ids = [int(r["post_id"]) for r in rows]
    placeholders = ",".join(["%s"] * len(post_ids))
    images_map = defaultdict(list)
    try:
        cur.execute(
            f"""
            SELECT post_id, image_path
            FROM post_images
            WHERE post_id IN ({placeholders})
            ORDER BY post_id, sort_order, image_id
            """,
            tuple(post_ids),
        )
        for row in cur.fetchall():
            images_map[int(row["post_id"])].append(row["image_path"])
    except Exception:
        images_map = defaultdict(list)

    saved_ids = set()
    if viewer:
        uid = int(viewer["user_id"])
        try:
            cur.execute(
                f"""
                SELECT post_id
                FROM user_saved_posts
                WHERE user_id = %s AND post_id IN ({placeholders})
                """,
                (uid, *post_ids),
            )
            saved_ids = {int(r["post_id"]) for r in cur.fetchall()}
        except Exception:
            saved_ids = set()

    for r in rows:
        pid = int(r["post_id"])
        gal = list(images_map.get(pid, []))
        if not gal and r.get("image_path"):
            gal = [r["image_path"]]
        r["gallery"] = gal
        r["user_has_saved"] = pid in saved_ids if viewer else False


def _insert_post_image_rows(cur, post_id, paths):
    if not paths:
        return
    for i, p in enumerate(paths):
        cur.execute(
            """
            INSERT INTO post_images (post_id, image_path, sort_order)
            VALUES (%s, %s, %s)
            """,
            (post_id, p, i),
        )


def _fetch_post_images(cur, post_id):
    try:
        cur.execute(
            """
            SELECT image_path
            FROM post_images
            WHERE post_id = %s
            ORDER BY sort_order, image_id
            """,
            (post_id,),
        )
        return [row["image_path"] for row in cur.fetchall()]
    except Exception:
        return []


def _replace_post_images(cur, post_id, paths):
    try:
        cur.execute("DELETE FROM post_images WHERE post_id = %s", (post_id,))
        _insert_post_image_rows(cur, post_id, paths)
    except Exception:
        pass


def _fetch_feed_sidebar(viewer):
    out = {
        "trending_schools": [],
        "upcoming_events": [],
        "suggested_orgs": [],
        "active_students": [],
    }
    sid = int(viewer["school_id"]) if viewer else None
    with db_cursor() as pair:
        if pair is None:
            return out
        _, cur = pair
        try:
            cur.execute(
                """
                SELECT s.school_id, s.name, COUNT(p.post_id) AS post_count
                FROM schools s
                INNER JOIN posts p ON p.school_id = s.school_id
                WHERE s.status = 'active'
                  AND p.created_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY s.school_id, s.name
                ORDER BY post_count DESC
                LIMIT 5
                """
            )
            out["trending_schools"] = cur.fetchall()
        except Exception:
            pass
        try:
            if sid is not None:
                cur.execute(
                    """
                    SELECT e.event_id, e.title, e.starts_at, s.name AS school_name
                    FROM events e
                    INNER JOIN schools s ON s.school_id = e.school_id
                    WHERE e.event_status = 'published'
                      AND e.starts_at > NOW()
                      AND (e.visibility = 'public' OR e.school_id = %s)
                    ORDER BY e.starts_at ASC
                    LIMIT 5
                    """,
                    (sid,),
                )
            else:
                cur.execute(
                    """
                    SELECT e.event_id, e.title, e.starts_at, s.name AS school_name
                    FROM events e
                    INNER JOIN schools s ON s.school_id = e.school_id
                    WHERE e.event_status = 'published'
                      AND e.starts_at > NOW()
                      AND e.visibility = 'public'
                    ORDER BY e.starts_at ASC
                    LIMIT 5
                    """
                )
            out["upcoming_events"] = cur.fetchall()
        except Exception:
            pass
        try:
            if sid is not None:
                cur.execute(
                    """
                    SELECT organization_id, name, slug
                    FROM organizations
                    WHERE status = 'active' AND school_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    (sid,),
                )
            else:
                cur.execute(
                    """
                    SELECT organization_id, name, slug
                    FROM organizations
                    WHERE status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                )
            out["suggested_orgs"] = cur.fetchall()
        except Exception:
            pass
        try:
            if sid is not None:
                cur.execute(
                    """
                    SELECT user_id, username, first_name, last_name, profile_image_url
                    FROM users
                    WHERE account_status = 'active' AND school_id = %s
                    ORDER BY last_seen_at IS NULL, last_seen_at DESC
                    LIMIT 8
                    """,
                    (sid,),
                )
            else:
                cur.execute(
                    """
                    SELECT user_id, username, first_name, last_name, profile_image_url
                    FROM users
                    WHERE account_status = 'active'
                    ORDER BY last_seen_at IS NULL, last_seen_at DESC
                    LIMIT 8
                    """
                )
            out["active_students"] = cur.fetchall()
        except Exception:
            pass
    return out


def _fetch_post_if_visible(post_id, viewer):
    vis_sql, vis_params = _visibility_sql_and_params(viewer)
    with db_cursor() as pair:
        if pair is None:
            return None
        conn, cur = pair
        cur.execute(
            f"""
            SELECT
                p.post_id,
                p.user_id,
                p.school_id,
                p.title
            FROM posts p
            WHERE p.post_id = %s AND {vis_sql}
            """,
            (post_id, *vis_params),
        )
        return cur.fetchone()


def _enrich_posts_with_social(rows, viewer):
    if not rows:
        return rows
    post_ids = [int(r["post_id"]) for r in rows]
    placeholders = ",".join(["%s"] * len(post_ids))
    uid = int(viewer["user_id"]) if viewer else None

    with db_cursor() as pair:
        if pair is None:
            for r in rows:
                r["like_count"] = 0
                r["user_has_liked"] = False
                r["comments"] = []
            return rows
        conn, cur = pair

        cur.execute(
            f"""
            SELECT target_id AS post_id, COUNT(*) AS cnt
            FROM reactions
            WHERE target_type = 'post'
              AND reaction_type = 'like'
              AND target_id IN ({placeholders})
            GROUP BY target_id
            """,
            tuple(post_ids),
        )
        likes_map = {int(row["post_id"]): int(row["cnt"]) for row in cur.fetchall()}

        user_liked = set()
        if uid is not None:
            cur.execute(
                f"""
                SELECT target_id
                FROM reactions
                WHERE user_id = %s
                  AND target_type = 'post'
                  AND reaction_type = 'like'
                  AND target_id IN ({placeholders})
                """,
                (uid, *post_ids),
            )
            user_liked = {int(row["target_id"]) for row in cur.fetchall()}

        cur.execute(
            f"""
            SELECT
                c.comment_id,
                c.post_id,
                c.user_id,
                c.parent_comment_id,
                c.content,
                c.created_at,
                u.username,
                u.first_name,
                u.last_name,
                u.profile_image_url AS author_profile_image
            FROM comments c
            INNER JOIN users u ON u.user_id = c.user_id
            WHERE c.post_id IN ({placeholders})
              AND c.parent_comment_id IS NULL
            ORDER BY c.post_id ASC, c.created_at ASC
            """,
            tuple(post_ids),
        )
        comment_rows = cur.fetchall()

        cur.execute(
            f"""
            SELECT
                c.comment_id,
                c.post_id,
                c.user_id,
                c.parent_comment_id,
                c.content,
                c.created_at,
                u.username,
                u.first_name,
                u.last_name,
                u.profile_image_url AS author_profile_image
            FROM comments c
            INNER JOIN users u ON u.user_id = c.user_id
            WHERE c.post_id IN ({placeholders})
              AND c.parent_comment_id IS NOT NULL
            ORDER BY c.post_id ASC, c.parent_comment_id ASC, c.created_at ASC
            """,
            tuple(post_ids),
        )
        reply_rows = cur.fetchall()

    replies_by_parent = defaultdict(list)
    for c in reply_rows:
        replies_by_parent[int(c["parent_comment_id"])].append(c)

    by_post = defaultdict(list)
    for c in comment_rows:
        cid = int(c["comment_id"])
        c["replies"] = replies_by_parent.get(cid, [])
        by_post[int(c["post_id"])].append(c)

    for r in rows:
        pid = int(r["post_id"])
        r["like_count"] = likes_map.get(pid, 0)
        r["user_has_liked"] = pid in user_liked if uid is not None else False
        r["comments"] = by_post.get(pid, [])
    return rows


def _redirect_feed():
    try:
        page = max(1, int(request.form.get("redirect_page", 1)))
    except (TypeError, ValueError):
        page = 1
    raw_school = request.form.get("redirect_school_id", "").strip()
    school_id = None
    if raw_school:
        try:
            school_id = int(raw_school)
        except ValueError:
            school_id = None
    compose = bool(request.form.get("redirect_compose"))
    return redirect(_feed_url(page, school_id, compose=compose))


def _can_delete_comment(comment_row):
    user = g.current_user
    if not user or not comment_row:
        return False
    if user.get("role") == "admin":
        return True
    return int(comment_row["user_id"]) == int(user["user_id"])


def _fetch_comment(comment_id):
    with db_cursor() as pair:
        if pair is None:
            return None
        conn, cur = pair
        cur.execute(
            """
            SELECT comment_id, post_id, user_id, content, parent_comment_id
            FROM comments
            WHERE comment_id = %s
            """,
            (comment_id,),
        )
        return cur.fetchone()


@posts_bp.route("/posts/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    post = _fetch_post_if_visible(post_id, g.current_user)
    if not post:
        flash("You cannot comment on this post.", "danger")
        return redirect(url_for("posts.feed"))

    content = request.form.get("content", "")
    err = validate_comment_content(content)
    if err:
        flash(err, "danger")
        return _redirect_feed()

    parent_raw = request.form.get("parent_comment_id", "").strip()
    parent_id = None
    if parent_raw:
        try:
            parent_id = int(parent_raw)
        except ValueError:
            parent_id = None
        if parent_id:
            with db_cursor() as pair:
                if pair is None:
                    flash("Cannot reach the database.", "danger")
                    return _redirect_feed()
                conn, cur = pair
                cur.execute(
                    """
                    SELECT comment_id FROM comments
                    WHERE comment_id = %s AND post_id = %s
                    """,
                    (parent_id, post_id),
                )
                if cur.fetchone() is None:
                    flash("Invalid reply target.", "danger")
                    return _redirect_feed()

    uid = int(g.current_user["user_id"])
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return _redirect_feed()
        conn, cur = pair
        cur.execute(
            """
            INSERT INTO comments (post_id, user_id, parent_comment_id, content, is_edited)
            VALUES (%s, %s, %s, %s, 0)
            """,
            (post_id, uid, parent_id, content.strip()),
        )
        conn.commit()

    flash("Comment added.", "success")
    return _redirect_feed()


@posts_bp.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    row = _fetch_comment(comment_id)
    if not row:
        flash("Comment not found.", "warning")
        return _redirect_feed()

    post = _fetch_post_if_visible(int(row["post_id"]), g.current_user)
    if not post:
        flash("You cannot modify this thread.", "danger")
        return _redirect_feed()

    if not _can_delete_comment(row):
        flash("You cannot delete this comment.", "danger")
        return _redirect_feed()

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return _redirect_feed()
        conn, cur = pair
        cur.execute(
            "SELECT comment_id FROM comments WHERE parent_comment_id = %s",
            (comment_id,),
        )
        child_ids = [int(r["comment_id"]) for r in cur.fetchall()]
        all_comment_ids = [comment_id] + child_ids
        placeholders = ",".join(["%s"] * len(all_comment_ids))
        cur.execute(
            f"""
            DELETE FROM reactions
            WHERE target_type = 'comment' AND target_id IN ({placeholders})
            """,
            tuple(all_comment_ids),
        )
        cur.execute(
            """
            DELETE FROM comments
            WHERE comment_id = %s OR parent_comment_id = %s
            """,
            (comment_id, comment_id),
        )
        conn.commit()

    flash("Comment removed.", "info")
    return _redirect_feed()


@posts_bp.route("/posts/<int:post_id>/react", methods=["POST"])
@login_required
def toggle_post_like(post_id):
    post = _fetch_post_if_visible(post_id, g.current_user)
    if not post:
        flash("You cannot react to this post.", "danger")
        return _redirect_feed()

    uid = int(g.current_user["user_id"])
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return _redirect_feed()
        conn, cur = pair
        cur.execute(
            """
            SELECT reaction_id, reaction_type
            FROM reactions
            WHERE user_id = %s AND target_type = 'post' AND target_id = %s
            """,
            (uid, post_id),
        )
        existing = cur.fetchone()

        if existing and existing.get("reaction_type") == "like":
            cur.execute(
                "DELETE FROM reactions WHERE reaction_id = %s",
                (existing["reaction_id"],),
            )
        else:
            if existing:
                cur.execute(
                    """
                    UPDATE reactions
                    SET reaction_type = 'like'
                    WHERE reaction_id = %s
                    """,
                    (existing["reaction_id"],),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO reactions (user_id, target_type, target_id, reaction_type)
                    VALUES (%s, 'post', %s, 'like')
                    """,
                    (uid, post_id),
                )
        conn.commit()

    return _redirect_feed()


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
            u.profile_image_url AS author_profile_image,
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
                feed_url=_feed_url,
                sidebar=_fetch_feed_sidebar(getattr(g, "current_user", None)),
                open_composer=bool(request.args.get("compose")),
            )

        conn, cur = pair
        cur.execute(count_sql, tuple(params))
        total = int(cur.fetchone()["c"])
        pages = max(1, math.ceil(total / per_page)) if total else 1
        page = min(page, pages)
        offset = (page - 1) * per_page

        cur.execute(list_sql, tuple(params + [per_page, offset]))
        rows = cur.fetchall()
        viewer = getattr(g, "current_user", None)
        _attach_gallery_and_saved(cur, rows, viewer)

    rows = _enrich_posts_with_social(rows, viewer)

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

    sidebar = _fetch_feed_sidebar(viewer)

    return render_template(
        "feed/index.html",
        posts=rows,
        schools_filter=_schools_for_filter(),
        school_filter=school_filter,
        pagination=pagination,
        feed_url=_feed_url,
        sidebar=sidebar,
        open_composer=bool(request.args.get("compose")),
    )


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
    if request.method == "GET":
        return redirect(url_for("posts.feed", compose=1))

    vals = _values_from_form()
    upload_folder = _posts_upload_dir()
    files = _get_request_image_files()
    saved_paths, upload_errors = save_post_images(files, upload_folder)
    for e in upload_errors:
        flash(e, "danger")
    img_url = _normalize_image_path(vals["image_path"])
    img = saved_paths[0] if saved_paths else img_url
    path_for_validation = "" if saved_paths else (img_url or "")
    errors = validate_post_form(
        vals["title"],
        vals["content"],
        path_for_validation,
        vals["category"],
        vals["privacy"],
    )
    if errors:
        for e in errors:
            flash(e, "danger")
        for rel in saved_paths:
            full = os.path.join(current_app.root_path, "static", rel)
            try:
                os.remove(full)
            except OSError:
                pass
        return redirect(url_for("posts.feed", compose=1))

    post_type = "image" if (img or saved_paths) else "text"
    uid = int(g.current_user["user_id"])
    sid = int(g.current_user["school_id"])

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("posts.feed", compose=1))
        conn, cur = pair
        try:
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
            if saved_paths:
                _insert_post_image_rows(cur, int(new_id), saved_paths)
            conn.commit()
        except Exception:
            conn.rollback()
            for rel in saved_paths:
                full = os.path.join(current_app.root_path, "static", rel)
                try:
                    os.remove(full)
                except OSError:
                    pass
            flash(
                "Could not publish the post. If you uploaded images, ensure migration "
                "005_post_images_saved_posts.sql has been applied.",
                "danger",
            )
            return redirect(url_for("posts.feed", compose=1))

    flash("Post published.", "success")
    return redirect(url_for("posts.feed"))


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

    gallery = []
    with db_cursor() as pair:
        if pair:
            _, cur = pair
            gallery = _fetch_post_images(cur, post_id)

    if request.method == "POST":
        vals = _values_from_form()
        files = _get_request_image_files()
        saved_paths, upload_errors = save_post_images(files, _posts_upload_dir())
        for e in upload_errors:
            flash(e, "danger")
        img_url = _normalize_image_path(vals["image_path"])
        if saved_paths:
            img = saved_paths[0]
        else:
            img = img_url if img_url is not None else (gallery[0] if gallery else None)
            if img is None and post.get("image_path"):
                img = post.get("image_path")

        path_for_validation = "" if saved_paths else (img_url or "")
        errors = validate_post_form(
            vals["title"],
            vals["content"],
            path_for_validation,
            vals["category"],
            vals["privacy"],
        )
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "posts/edit.html",
                post=post,
                values=vals,
                gallery=gallery,
            )

        post_type = "image" if (img or saved_paths or gallery) else "text"

        with db_cursor() as pair:
            if pair is None:
                flash("Cannot reach the database.", "danger")
                return render_template(
                    "posts/edit.html",
                    post=post,
                    values=vals,
                    gallery=gallery,
                )
            conn, cur = pair
            try:
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
                if saved_paths:
                    _replace_post_images(cur, post_id, saved_paths)
                conn.commit()
            except Exception:
                conn.rollback()
                flash(
                    "Could not update images. Ensure migration 005_post_images_saved_posts.sql is applied.",
                    "danger",
                )
                return render_template(
                    "posts/edit.html",
                    post=post,
                    values=vals,
                    gallery=gallery,
                )

        flash("Post updated.", "success")
        return redirect(url_for("posts.feed"))

    return render_template(
        "posts/edit.html",
        post=post,
        values=_values_from_post_row(post),
        gallery=gallery,
    )


@posts_bp.route("/posts/<int:post_id>/save", methods=["POST"])
@login_required
def toggle_save_post(post_id):
    post = _fetch_post_if_visible(post_id, g.current_user)
    if not post:
        flash("You cannot bookmark this post.", "danger")
        return _redirect_feed()
    uid = int(g.current_user["user_id"])
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return _redirect_feed()
        conn, cur = pair
        try:
            cur.execute(
                "SELECT 1 FROM user_saved_posts WHERE user_id = %s AND post_id = %s",
                (uid, post_id),
            )
            if cur.fetchone():
                cur.execute(
                    "DELETE FROM user_saved_posts WHERE user_id = %s AND post_id = %s",
                    (uid, post_id),
                )
                flash("Removed from saved posts.", "info")
            else:
                cur.execute(
                    "INSERT INTO user_saved_posts (user_id, post_id) VALUES (%s, %s)",
                    (uid, post_id),
                )
                flash("Post saved.", "success")
            conn.commit()
        except Exception:
            flash(
                "Saved posts require database migration 005_post_images_saved_posts.sql.",
                "danger",
            )
    return _redirect_feed()


@posts_bp.route("/posts/<int:post_id>/report", methods=["POST"])
@login_required
def report_post(post_id):
    post = _fetch_post_if_visible(post_id, g.current_user)
    if not post:
        flash("You cannot report this post.", "danger")
        return _redirect_feed()
    flash("Thanks — your report has been recorded.", "info")
    return _redirect_feed()


@posts_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    after_delete = redirect(
        safe_next_path(request.form.get("next")) or url_for("posts.feed")
    )

    post = _fetch_post(post_id)
    if not post:
        flash("Post not found.", "warning")
        return after_delete

    if not _can_manage_post(post):
        flash("You cannot delete this post.", "danger")
        return after_delete

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return after_delete
        conn, cur = pair
        cur.execute("DELETE FROM posts WHERE post_id = %s", (post_id,))
        conn.commit()

    flash("Post deleted.", "info")
    return after_delete
