from flask import g, session

from utils.auth_helpers import fetch_user_by_id


def init_session_middleware(app):
    @app.before_request
    def load_logged_in_user():
        g.current_user = None
        uid = session.get("user_id")
        if not uid:
            return
        user = fetch_user_by_id(uid)
        if user and user.get("account_status") == "active":
            g.current_user = user
        else:
            session.pop("user_id", None)

    @app.context_processor
    def inject_current_user():
        return {"current_user": getattr(g, "current_user", None)}
