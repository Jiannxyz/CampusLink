from flask import Flask, render_template, url_for

from config import Config
from utils.static_paths import media_public_url, normalize_static_path
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.events import events_bp
from routes.main import main_bp
from routes.posts import posts_bp
from routes.profiles import profiles_bp
from routes.schools import schools_bp
from routes.search import search_bp
from utils.session_middleware import init_session_middleware


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_session_middleware(app)

    @app.template_filter("normalize_static_path")
    def _normalize_static_path_filter(raw):
        return normalize_static_path(raw)

    @app.template_global()
    def media_url(path):
        return media_public_url(path, url_for)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(schools_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html", error=error), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
