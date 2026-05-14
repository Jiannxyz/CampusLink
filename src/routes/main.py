from flask import Blueprint, g, redirect, render_template, url_for

from utils.auth_helpers import login_required
from utils.db import db_cursor

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    if getattr(g, "current_user", None):
        return redirect(url_for("posts.feed"))
    return render_template("index.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/organizations")
def organizations():
    rows = []
    with db_cursor() as pair:
        if pair:
            _, cur = pair
            cur.execute(
                """
                SELECT o.organization_id, o.name, o.slug, o.description, s.name AS school_name
                FROM organizations o
                INNER JOIN schools s ON s.school_id = o.school_id
                WHERE o.status = 'active' AND s.status = 'active'
                ORDER BY o.name ASC
                LIMIT 200
                """
            )
            rows = cur.fetchall()
    return render_template("main/organizations.html", organizations=rows)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")
