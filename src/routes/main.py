from flask import Blueprint, flash, render_template

from utils.auth_helpers import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("index.html")


@main_bp.route("/about")
def about():
    flash("Welcome to the CampusLink demo app!", "info")
    return render_template("about.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")
