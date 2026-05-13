"""
Reusable search utilities: keyword sanitization, SQL LIKE patterns, pagination.
"""

import math

POST_CATEGORIES = (
    "general",
    "academic",
    "events",
    "clubs",
    "questions",
    "marketplace",
)
EVENT_STATUSES = ("draft", "published", "cancelled", "completed")
USER_ROLES = ("student", "staff", "admin")
SEARCH_SCOPES = ("all", "schools", "users", "posts", "events")


def sanitize_keyword(raw, min_len=2, max_len=100):
    if raw is None:
        return None
    s = str(raw).strip()
    if len(s) < min_len or len(s) > max_len:
        return None
    return s


def like_contains(keyword):
    """
    Build a LIKE pattern with % wildcards; escape \, %, and _ for MySQL LIKE.
    """
    if not keyword:
        return None
    esc = (
        keyword.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{esc}%"


def pagination_dict(page, per_page, total):
    pages = max(1, math.ceil(total / per_page)) if total else 1
    page = min(max(1, page), pages)
    return {
        "page": page,
        "pages": pages,
        "total": total,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if page < pages else None,
    }


def post_visibility_sql(viewer):
    """Same rules as the public feed for post rows (alias p.)."""
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


def event_search_visibility_sql(viewer):
    """Published events visible like the upcoming list (alias e.)."""
    if viewer is None:
        return "e.visibility = 'public'", []
    sid = int(viewer["school_id"])
    return (
        "(e.visibility = 'public' OR (e.visibility IN ('school_only', 'organization_only') AND e.school_id = %s))",
        [sid],
    )
