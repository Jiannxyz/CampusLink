from flask import Flask, render_template

from config import Config
from routes.main import main_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html", error=error), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
