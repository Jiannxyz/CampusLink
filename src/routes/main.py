from flask import Blueprint, flash, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("index.html")


@main_bp.route("/about")
def about():
    flash("Welcome to the CampusLink demo app!", "info")
    return render_template("about.html")
