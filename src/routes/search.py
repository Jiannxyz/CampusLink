from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    render_template,
    request,
    url_for,
)

from utils.db import db_cursor
from utils.search_helpers import (
    EVENT_STATUSES,
    POST_CATEGORIES,
    USER_ROLES,
    event_search_visibility_sql,
    like_contains,
    pagination_dict,
    post_visibility_sql,
    sanitize_keyword,
)

search_bp = Blueprint("search", __name__, url_prefix="/search")


def _search_url(**overrides):
    args = request.args.to_dict(flat=True)
    args.update({k: str(v) for k, v in overrides.items() if v is not None})
    for k, v in list(args.items()):
        if v == "":
            del args[k]
    return url_for("search.search", **args)


def _active_schools_options():
    with db_cursor() as pair:
        if pair is None:
            return []
        conn, cur = pair
        cur.execute(
            "SELECT school_id, name FROM schools WHERE status = 'active' ORDER BY name"
        )
        return cur.fetchall()


def _search_schools(pattern, school_id, limit, offset=None):
    where = ["s.status = 'active'"]
    params = []
    if pattern:
        where.append(
            """(
            s.name LIKE %s OR s.school_code LIKE %s OR s.city LIKE %s OR s.campus LIKE %s
            OR IFNULL(s.description, '') LIKE %s OR s.email_domain LIKE %s
            OR IFNULL(s.province, '') LIKE %s OR IFNULL(s.country, '') LIKE %s
        )"""
        )
        params.extend([pattern] * 8)
    if school_id is not None:
        where.append("s.school_id = %s")
        params.append(school_id)
    wh = " AND ".join(where)
    from_clause = f"schools s WHERE {wh}"
    with db_cursor() as pair:
        if pair is None:
            return [], 0
        conn, cur = pair
        cur.execute(f"SELECT COUNT(*) AS c FROM {from_clause}", tuple(params))
        total = int(cur.fetchone()["c"])
        sql = f"""
            SELECT s.school_id, s.name, s.school_code, s.city, s.campus, s.status
            FROM {from_clause}
            ORDER BY s.name ASC
        """
        if offset is not None:
            sql += " LIMIT %s OFFSET %s"
            cur.execute(sql, tuple(params + [limit, offset]))
        else:
            sql += " LIMIT %s"
            cur.execute(sql, tuple(params + [limit]))
        return cur.fetchall(), total


def _search_users(pattern, school_id, user_role, viewer, limit, offset=None):
    if viewer is None:
        return [], 0
    where = ["u.account_status = 'active'"]
    params = []
    if viewer.get("role") != "admin":
        where.append("u.school_id = %s")
        params.append(int(viewer["school_id"]))
    if pattern:
        where.append(
            """(
            u.username LIKE %s OR u.first_name LIKE %s OR u.last_name LIKE %s
            OR CONCAT(u.first_name, ' ', u.last_name) LIKE %s
            OR IFNULL(u.bio, '') LIKE %s
        )"""
        )
        params.extend([pattern] * 5)
    if school_id is not None:
        where.append("u.school_id = %s")
        params.append(school_id)
    if user_role and user_role in USER_ROLES:
        where.append("u.role = %s")
        params.append(user_role)
    wh = " AND ".join(where)
    from_clause = f"users u INNER JOIN schools sch ON sch.school_id = u.school_id WHERE {wh}"
    with db_cursor() as pair:
        if pair is None:
            return [], 0
        conn, cur = pair
        cur.execute(f"SELECT COUNT(*) AS c FROM {from_clause}", tuple(params))
        total = int(cur.fetchone()["c"])
        sql = f"""
            SELECT u.user_id, u.username, u.first_name, u.last_name, u.role,
                   sch.name AS school_name
            FROM {from_clause}
            ORDER BY u.username ASC
        """
        if offset is not None:
            sql += " LIMIT %s OFFSET %s"
            cur.execute(sql, tuple(params + [limit, offset]))
        else:
            sql += " LIMIT %s"
            cur.execute(sql, tuple(params + [limit]))
        return cur.fetchall(), total


def _search_posts(pattern, post_category, school_id, viewer, limit, offset=None):
    vis_sql, vis_params = post_visibility_sql(viewer)
    where = [vis_sql]
    params = list(vis_params)
    if pattern:
        where.append("(p.title LIKE %s OR p.content LIKE %s)")
        params.extend([pattern, pattern])
    if post_category and post_category in POST_CATEGORIES:
        where.append("p.category = %s")
        params.append(post_category)
    if school_id is not None:
        where.append("p.school_id = %s")
        params.append(school_id)
    wh = " AND ".join(where)
    from_clause = f"""posts p
            INNER JOIN users u ON u.user_id = p.user_id
            INNER JOIN schools sch ON sch.school_id = p.school_id
            WHERE {wh}"""
    with db_cursor() as pair:
        if pair is None:
            return [], 0
        conn, cur = pair
        cur.execute(f"SELECT COUNT(*) AS c FROM {from_clause}", tuple(params))
        total = int(cur.fetchone()["c"])
        sql = f"""
            SELECT p.post_id, p.title, p.category, p.privacy, p.created_at,
                   u.username, sch.name AS school_name
            FROM {from_clause}
            ORDER BY p.created_at DESC
        """
        if offset is not None:
            sql += " LIMIT %s OFFSET %s"
            cur.execute(sql, tuple(params + [limit, offset]))
        else:
            sql += " LIMIT %s"
            cur.execute(sql, tuple(params + [limit]))
        return cur.fetchall(), total


def _search_events(pattern, event_status, school_id, viewer, limit, offset=None):
    vis_sql, vis_params = event_search_visibility_sql(viewer)
    where = [vis_sql]
    params = list(vis_params)
    is_admin = viewer and viewer.get("role") == "admin"
    if event_status and event_status in EVENT_STATUSES and is_admin:
        where.append("e.event_status = %s")
        params.append(event_status)
    else:
        where.append("e.event_status = 'published'")
    if pattern:
        where.append(
            "(e.title LIKE %s OR IFNULL(e.description, '') LIKE %s OR IFNULL(e.location, '') LIKE %s)"
        )
        params.extend([pattern, pattern, pattern])
    if school_id is not None:
        where.append("e.school_id = %s")
        params.append(school_id)
    wh = " AND ".join(where)
    from_clause = f"""events e
            INNER JOIN schools sch ON sch.school_id = e.school_id
            WHERE {wh}"""
    with db_cursor() as pair:
        if pair is None:
            return [], 0
        conn, cur = pair
        cur.execute(f"SELECT COUNT(*) AS c FROM {from_clause}", tuple(params))
        total = int(cur.fetchone()["c"])
        sql = f"""
            SELECT e.event_id, e.title, e.location, e.starts_at, e.event_status,
                   e.visibility, sch.name AS school_name
            FROM {from_clause}
            ORDER BY e.starts_at ASC
        """
        if offset is not None:
            sql += " LIMIT %s OFFSET %s"
            cur.execute(sql, tuple(params + [limit, offset]))
        else:
            sql += " LIMIT %s"
            cur.execute(sql, tuple(params + [limit]))
        return cur.fetchall(), total


@search_bp.route("/")
def search():
    per_page = current_app.config.get("SEARCH_PER_PAGE", 10)
    preview = current_app.config.get("SEARCH_PREVIEW", 5)
    q_raw = request.args.get("q", "")
    scope = (request.args.get("type") or "all").strip().lower()
    if scope not in ("all", "schools", "users", "posts", "events"):
        scope = "all"

    post_category = (request.args.get("post_category") or "").strip().lower()
    if post_category and post_category not in POST_CATEGORIES:
        post_category = ""

    event_status = (request.args.get("event_status") or "").strip().lower()
    if event_status and event_status not in EVENT_STATUSES:
        event_status = ""

    user_role = (request.args.get("user_role") or "").strip().lower()
    if user_role and user_role not in USER_ROLES:
        user_role = ""

    school_id = None
    raw_school = request.args.get("school_id", "").strip()
    if raw_school:
        try:
            school_id = int(raw_school)
        except ValueError:
            school_id = None

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    keyword = sanitize_keyword(q_raw)
    pattern = like_contains(keyword) if keyword else None
    has_query = bool(keyword)

    if not keyword and scope != "all":
        flash("Enter at least 2 characters to search.", "warning")

    schools_opts = _active_schools_options()
    viewer = getattr(g, "current_user", None)

    results = {
        "schools": [],
        "users": [],
        "posts": [],
        "events": [],
    }
    pagination = None

    if not keyword:
        return render_template(
            "search/index.html",
            q=q_raw,
            has_query=False,
            scope=scope,
            post_category=post_category,
            event_status=event_status,
            user_role=user_role,
            school_id=school_id,
            schools_filter=schools_opts,
            results=results,
            pagination=None,
            search_url=_search_url,
        )

    if scope == "all":
        results["schools"], _ = _search_schools(pattern, school_id, preview, None)
        results["users"], _ = _search_users(pattern, school_id, user_role, viewer, preview, None)
        results["posts"], _ = _search_posts(pattern, post_category, school_id, viewer, preview, None)
        results["events"], _ = _search_events(pattern, event_status, school_id, viewer, preview, None)
    elif scope == "schools":
        rows, total = _search_schools(pattern, school_id, per_page, (page - 1) * per_page)
        pagination = pagination_dict(page, per_page, total)
        if pagination["page"] != page:
            rows, total = _search_schools(
                pattern, school_id, per_page, (pagination["page"] - 1) * per_page
            )
        results["schools"] = rows
    elif scope == "users":
        rows, total = _search_users(
            pattern, school_id, user_role, viewer, per_page, (page - 1) * per_page
        )
        pagination = pagination_dict(page, per_page, total)
        if pagination["page"] != page:
            rows, total = _search_users(
                pattern,
                school_id,
                user_role,
                viewer,
                per_page,
                (pagination["page"] - 1) * per_page,
            )
        results["users"] = rows
    elif scope == "posts":
        rows, total = _search_posts(
            pattern, post_category, school_id, viewer, per_page, (page - 1) * per_page
        )
        pagination = pagination_dict(page, per_page, total)
        if pagination["page"] != page:
            rows, total = _search_posts(
                pattern,
                post_category,
                school_id,
                viewer,
                per_page,
                (pagination["page"] - 1) * per_page,
            )
        results["posts"] = rows
    elif scope == "events":
        rows, total = _search_events(
            pattern, event_status, school_id, viewer, per_page, (page - 1) * per_page
        )
        pagination = pagination_dict(page, per_page, total)
        if pagination["page"] != page:
            rows, total = _search_events(
                pattern,
                event_status,
                school_id,
                viewer,
                per_page,
                (pagination["page"] - 1) * per_page,
            )
        results["events"] = rows

    return render_template(
        "search/index.html",
        q=q_raw,
        has_query=True,
        scope=scope,
        post_category=post_category,
        event_status=event_status,
        user_role=user_role,
        school_id=school_id,
        schools_filter=schools_opts,
        results=results,
        pagination=pagination,
        search_url=_search_url,
    )
