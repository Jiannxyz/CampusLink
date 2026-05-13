from flask import Flask, render_template

from config import Config
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.main import main_bp
from routes.schools import schools_bp
from utils.session_middleware import init_session_middleware


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_session_middleware(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(schools_bp)
    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html", error=error), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
