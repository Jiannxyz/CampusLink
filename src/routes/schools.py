from mysql.connector import IntegrityError

from flask import Blueprint, flash, redirect, render_template, request, url_for

from utils.auth_helpers import admin_required
from utils.db import db_cursor
from utils.school_validation import validate_school_form

schools_bp = Blueprint("schools", __name__, url_prefix="/schools")

SCHOOL_FORM_KEYS = (
    "name",
    "school_code",
    "email_domain",
    "campus",
    "city",
    "province",
    "country",
    "description",
    "logo_path",
    "status",
)


def _empty_values():
    d = {k: "" for k in SCHOOL_FORM_KEYS}
    d["status"] = "active"
    return d


def _values_from_form():
    d = {}
    for k in SCHOOL_FORM_KEYS:
        if k == "description":
            d[k] = request.form.get(k) or ""
        else:
            d[k] = (request.form.get(k) or "").strip()
    return d


def _values_from_school(row):
    d = {}
    for k in SCHOOL_FORM_KEYS:
        v = row.get(k)
        d[k] = "" if v is None else str(v)
    return d


def _normalize_logo_path(raw):
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    if s.startswith("/static/"):
        return s[len("/static/") :]
    return s


@schools_bp.route("/")
@admin_required
def list_schools():
    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return render_template("schools/list.html", schools=[])

        conn, cur = pair
        cur.execute(
            """
            SELECT
                s.school_id,
                s.school_code,
                s.name,
                s.campus,
                s.city,
                s.province,
                s.country,
                s.status,
                s.logo_path,
                (SELECT COUNT(*) FROM users u WHERE u.school_id = s.school_id) AS user_count
            FROM schools s
            ORDER BY s.name
            """
        )
        schools = cur.fetchall()

    return render_template("schools/list.html", schools=schools)


@schools_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_school():
    if request.method == "POST":
        vals = _values_from_form()
        name = vals["name"]
        school_code = vals["school_code"]
        email_domain = vals["email_domain"].lower()
        campus = vals["campus"] or None
        city = vals["city"] or None
        province = vals["province"] or None
        country = vals["country"] or None
        description = (vals["description"] or "").strip() or None
        logo_path = _normalize_logo_path(vals["logo_path"])
        status = vals["status"] or "active"

        errors = validate_school_form(
            name,
            school_code,
            email_domain,
            campus or "",
            city or "",
            province or "",
            country or "",
            description or "",
            logo_path or "",
            status,
        )
        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template("schools/create.html", values=vals)

        try:
            with db_cursor() as pair:
                if pair is None:
                    flash("Cannot reach the database.", "danger")
                    return render_template("schools/create.html", values=vals)

                conn, cur = pair
                cur.execute(
                    """
                    INSERT INTO schools (
                        school_code, name, campus, email_domain,
                        city, province, country, description, logo_path, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        school_code,
                        name,
                        campus,
                        email_domain,
                        city,
                        province,
                        country,
                        description,
                        logo_path,
                        status,
                    ),
                )
                new_id = cur.lastrowid
                conn.commit()

            flash("School created successfully.", "success")
            return redirect(url_for("schools.school_detail", school_id=new_id))

        except IntegrityError:
            flash("School code or email domain is already in use.", "danger")
            return render_template("schools/create.html", values=vals)

    return render_template("schools/create.html", values=_empty_values())


@schools_bp.route("/<int:school_id>")
@admin_required
def school_detail(school_id):
    school = _fetch_school(school_id)
    if not school:
        flash("School not found.", "warning")
        return redirect(url_for("schools.list_schools"))
    return render_template("schools/detail.html", school=school)


@schools_bp.route("/<int:school_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_school(school_id):
    school = _fetch_school(school_id)
    if not school:
        flash("School not found.", "warning")
        return redirect(url_for("schools.list_schools"))

    if request.method == "POST":
        vals = _values_from_form()
        name = vals["name"]
        school_code = vals["school_code"]
        email_domain = vals["email_domain"].lower()
        campus = vals["campus"] or None
        city = vals["city"] or None
        province = vals["province"] or None
        country = vals["country"] or None
        description = (vals["description"] or "").strip() or None
        logo_path = _normalize_logo_path(vals["logo_path"])
        status = vals["status"] or "active"

        errors = validate_school_form(
            name,
            school_code,
            email_domain,
            campus or "",
            city or "",
            province or "",
            country or "",
            description or "",
            logo_path or "",
            status,
        )
        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template(
                "schools/edit.html",
                school=school,
                values=vals,
            )

        try:
            with db_cursor() as pair:
                if pair is None:
                    flash("Cannot reach the database.", "danger")
                    return render_template(
                        "schools/edit.html",
                        school=school,
                        values=vals,
                    )

                conn, cur = pair
                cur.execute(
                    """
                    UPDATE schools SET
                        school_code = %s,
                        name = %s,
                        campus = %s,
                        email_domain = %s,
                        city = %s,
                        province = %s,
                        country = %s,
                        description = %s,
                        logo_path = %s,
                        status = %s
                    WHERE school_id = %s
                    """,
                    (
                        school_code,
                        name,
                        campus,
                        email_domain,
                        city,
                        province,
                        country,
                        description,
                        logo_path,
                        status,
                        school_id,
                    ),
                )
                conn.commit()

            flash("School updated successfully.", "success")
            return redirect(url_for("schools.school_detail", school_id=school_id))

        except IntegrityError:
            flash("School code or email domain is already in use.", "danger")
            return render_template(
                "schools/edit.html",
                school=school,
                values=vals,
            )

    return render_template(
        "schools/edit.html",
        school=school,
        values=_values_from_school(school),
    )


@schools_bp.route("/<int:school_id>/delete", methods=["POST"])
@admin_required
def delete_school(school_id):
    school = _fetch_school(school_id)
    if not school:
        flash("School not found.", "warning")
        return redirect(url_for("schools.list_schools"))

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("schools.school_detail", school_id=school_id))

        conn, cur = pair
        cur.execute(
            "SELECT COUNT(*) AS c FROM users WHERE school_id = %s",
            (school_id,),
        )
        row = cur.fetchone()
        if row and row.get("c", 0) > 0:
            flash(
                "Cannot delete this school while users are assigned to it. "
                "Deactivate the school or reassign users first.",
                "danger",
            )
            return redirect(url_for("schools.school_detail", school_id=school_id))

        try:
            cur.execute(
                "DELETE FROM schools WHERE school_id = %s",
                (school_id,),
            )
            conn.commit()
        except IntegrityError:
            flash(
                "Cannot delete this school because other records still reference it.",
                "danger",
            )
            return redirect(url_for("schools.school_detail", school_id=school_id))

    flash("School deleted.", "success")
    return redirect(url_for("schools.list_schools"))


def _fetch_school(school_id):
    with db_cursor() as pair:
        if pair is None:
            return None
        conn, cur = pair
        cur.execute(
            """
            SELECT
                s.*,
                (SELECT COUNT(*) FROM users u WHERE u.school_id = s.school_id) AS user_count
            FROM schools s
            WHERE s.school_id = %s
            """,
            (school_id,),
        )
        return cur.fetchone()
