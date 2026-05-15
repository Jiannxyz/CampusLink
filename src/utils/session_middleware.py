import time

from flask import g, session

from utils.auth_helpers import fetch_user_by_id
from utils.db import db_cursor
from utils.static_paths import normalize_static_path

_LAST_SEEN_SESSION_KEY = "_profile_last_seen_bump"
_LAST_SEEN_INTERVAL_SEC = 120


def init_session_middleware(app):
    @app.before_request
    def load_logged_in_user():
        g.current_user = None
        uid = session.get("user_id")
        if not uid:
            return
        user = fetch_user_by_id(uid)
        if user and user.get("account_status") == "active":
            if user.get("profile_image_url") is not None:
                user["profile_image_url"] = normalize_static_path(
                    user["profile_image_url"]
                )
            if user.get("cover_image_path") is not None:
                user["cover_image_path"] = normalize_static_path(
                    user["cover_image_path"]
                )
            g.current_user = user
            _maybe_bump_last_seen(int(uid))
        else:
            session.pop("user_id", None)

    @app.context_processor
    def inject_current_user():
        return {"current_user": getattr(g, "current_user", None)}


def _maybe_bump_last_seen(user_id):
    now = time.time()
    last = session.get(_LAST_SEEN_SESSION_KEY, 0)
    if now - last < _LAST_SEEN_INTERVAL_SEC:
        return
    with db_cursor() as pair:
        if pair is None:
            return
        conn, cur = pair
        try:
            cur.execute(
                "UPDATE users SET last_seen_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                (user_id,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
    session[_LAST_SEEN_SESSION_KEY] = now
