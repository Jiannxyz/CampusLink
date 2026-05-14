import math
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from utils.auth_helpers import login_required
from utils.db import db_cursor
from utils.event_validation import parse_event_datetime, validate_event_form

events_bp = Blueprint("events", __name__, url_prefix="/events")


def _now():
    return datetime.now()


def _can_manage_event(row):
    u = g.current_user
    if not u or not row:
        return False
    if u.get("role") == "admin":
        return True
    return int(row["created_by_user_id"]) == int(u["user_id"])


def _schools_active():
    with db_cursor() as pair:
        if pair is None:
            return []
        conn, cur = pair
        cur.execute(
            """
            SELECT school_id, name FROM schools
            WHERE status = 'active' ORDER BY name
            """
        )
        return cur.fetchall()


def _parse_capacity(raw):
    s = (raw or "").strip()
    if not s:
        return None
    try:
        v = int(s)
        return v if v >= 1 else None
    except ValueError:
        return -1


def _parse_org_id(raw):
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _listing_visibility_clause(viewer):
    if viewer is None:
        return "e.visibility = 'public'", []
    sid = int(viewer["school_id"])
    return (
        "(e.visibility = 'public' OR (e.visibility IN ('school_only', 'organization_only') AND e.school_id = %s))",
        [sid],
    )


def _can_view_event_detail(row, viewer):
    if not row:
        return False
    st = row.get("event_status")
    if st == "draft":
        if not viewer:
            return False
        if viewer.get("role") == "admin":
            return True
        return int(row["created_by_user_id"]) == int(viewer["user_id"])
    if st in ("cancelled", "completed"):
        return _can_manage_event(row) or _event_list_visible(row, viewer)
    return _event_list_visible(row, viewer)


def _event_list_visible(row, viewer):
    if row.get("event_status") != "published":
        return False
    vis = row.get("visibility")
    if vis == "public":
        return True
    if not viewer:
        return False
    return int(row["school_id"]) == int(viewer["school_id"])


def _fetch_event(event_id):
    with db_cursor() as pair:
        if pair is None:
            return None
        conn, cur = pair
        cur.execute(
            """
            SELECT
                e.*,
                s.name AS school_name,
                u.username AS organizer_username,
                u.first_name AS organizer_first_name,
                u.last_name AS organizer_last_name,
                (SELECT COUNT(*) FROM event_rsvps er
                 WHERE er.event_id = e.event_id AND er.status = 'going') AS attendee_count
            FROM events e
            INNER JOIN schools s ON s.school_id = e.school_id
            INNER JOIN users u ON u.user_id = e.created_by_user_id
            WHERE e.event_id = %s
            """,
            (event_id,),
        )
        return cur.fetchone()


def _user_rsvp(event_id, user_id):
    with db_cursor() as pair:
        if pair is None:
            return None
        conn, cur = pair
        cur.execute(
            """
            SELECT status FROM event_rsvps
            WHERE event_id = %s AND user_id = %s
            """,
            (event_id, user_id),
        )
        row = cur.fetchone()
        return row["status"] if row else None


@events_bp.route("/upcoming")
def upcoming():
    per_page = current_app.config.get("EVENTS_PER_PAGE", 12)
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    viewer = getattr(g, "current_user", None)
    vis_sql, vis_params = _listing_visibility_clause(viewer)

    where = f"""
        e.event_status = 'published'
        AND e.starts_at >= NOW()
        AND {vis_sql}
    """
    count_sql = f"SELECT COUNT(*) AS c FROM events e WHERE {where}"
    list_sql = f"""
        SELECT
            e.event_id,
            e.title,
            e.description,
            e.location,
            e.starts_at,
            e.ends_at,
            e.visibility,
            e.capacity,
            e.school_id,
            s.name AS school_name,
            u.username AS organizer_username,
            (SELECT COUNT(*) FROM event_rsvps er
             WHERE er.event_id = e.event_id AND er.status = 'going') AS attendee_count
        FROM events e
        INNER JOIN schools s ON s.school_id = e.school_id
        INNER JOIN users u ON u.user_id = e.created_by_user_id
        WHERE {where}
        ORDER BY e.starts_at ASC
        LIMIT %s OFFSET %s
    """

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return render_template(
                "events/upcoming.html",
                events=[],
                pagination=None,
            )
        conn, cur = pair
        params = list(vis_params)
        cur.execute(count_sql, tuple(params))
        total = int(cur.fetchone()["c"])
        pages = max(1, math.ceil(total / per_page)) if total else 1
        page = min(page, pages)
        offset = (page - 1) * per_page
        cur.execute(list_sql, tuple(params + [per_page, offset]))
        rows = cur.fetchall()

    pagination = {
        "page": page,
        "pages": pages,
        "total": total,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if page < pages else None,
    }

    return render_template(
        "events/upcoming.html",
        events=rows,
        pagination=pagination,
    )


@events_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_event():
    schools = _schools_active() if g.current_user.get("role") == "admin" else None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        venue = (request.form.get("venue") or "").strip() or None
        starts = parse_event_datetime(request.form.get("starts_at"))
        ends_raw = request.form.get("ends_at")
        ends = parse_event_datetime(ends_raw) if ends_raw else None
        visibility = (request.form.get("visibility") or "school_only").strip()
        event_status = (request.form.get("event_status") or "draft").strip()
        cap = _parse_capacity(request.form.get("capacity"))
        org_id = _parse_org_id(request.form.get("organization_id"))

        now = _now()
        errors = validate_event_form(
            title,
            description or "",
            venue or "",
            starts,
            ends,
            visibility,
            event_status,
            cap if cap != -1 else None,
            now,
            require_future_start_if_published=True,
        )
        if cap == -1:
            errors.append("Capacity must be a positive number or empty.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "events/create.html",
                schools=schools,
                form=request.form,
            )

        if g.current_user.get("role") == "admin":
            try:
                school_id = int(request.form.get("school_id", ""))
            except (TypeError, ValueError):
                flash("Choose a valid school.", "danger")
                return render_template(
                    "events/create.html",
                    schools=schools,
                    form=request.form,
                )
        else:
            school_id = int(g.current_user["school_id"])

        uid = int(g.current_user["user_id"])

        with db_cursor() as pair:
            if pair is None:
                flash("Cannot reach the database.", "danger")
                return render_template(
                    "events/create.html",
                    schools=schools,
                    form=request.form,
                )
            conn, cur = pair
            cur.execute(
                "SELECT 1 FROM schools WHERE school_id = %s AND status = 'active'",
                (school_id,),
            )
            if cur.fetchone() is None:
                flash("Invalid school.", "danger")
                return render_template(
                    "events/create.html",
                    schools=schools,
                    form=request.form,
                )
            if org_id:
                cur.execute(
                    """
                    SELECT 1 FROM organizations
                    WHERE organization_id = %s AND school_id = %s AND status = 'active'
                    """,
                    (org_id, school_id),
                )
                if cur.fetchone() is None:
                    org_id = None

            cur.execute(
                """
                INSERT INTO events (
                    school_id, organization_id, created_by_user_id,
                    title, description, location, starts_at, ends_at,
                    visibility, event_status, capacity
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    school_id,
                    org_id,
                    uid,
                    title,
                    description,
                    venue,
                    starts,
                    ends,
                    visibility,
                    event_status,
                    cap,
                ),
            )
            new_id = cur.lastrowid
            conn.commit()

        flash("Event created.", "success")
        return redirect(url_for("events.event_detail", event_id=new_id))

    return render_template("events/create.html", schools=schools, form=None)


@events_bp.route("/<int:event_id>")
def event_detail(event_id):
    row = _fetch_event(event_id)
    if not row or not _can_view_event_detail(row, getattr(g, "current_user", None)):
        flash("Event not found or you do not have access.", "warning")
        return redirect(url_for("events.upcoming"))

    rsvp_status = None
    event_saved = False
    if g.current_user:
        uid = int(g.current_user["user_id"])
        rsvp_status = _user_rsvp(event_id, uid)
        try:
            with db_cursor() as pair:
                if pair:
                    _, cur = pair
                    cur.execute(
                        """
                        SELECT 1 FROM user_saved_events
                        WHERE user_id = %s AND event_id = %s
                        """,
                        (uid, event_id),
                    )
                    event_saved = cur.fetchone() is not None
        except Exception:
            event_saved = False

    st = row.get("starts_at")
    allow_rsvp = (
        row.get("event_status") == "published"
        and st is not None
        and (st.replace(tzinfo=None) if getattr(st, "tzinfo", None) else st) > _now()
    )

    return render_template(
        "events/detail.html",
        event=row,
        rsvp_status=rsvp_status,
        can_manage=_can_manage_event(row),
        allow_rsvp=allow_rsvp,
        event_saved=event_saved,
    )


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    row = _fetch_event(event_id)
    if not row:
        flash("Event not found.", "warning")
        return redirect(url_for("events.upcoming"))
    if not _can_manage_event(row):
        flash("You cannot edit this event.", "danger")
        return redirect(url_for("events.event_detail", event_id=event_id))

    schools = _schools_active() if g.current_user.get("role") == "admin" else None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        venue = (request.form.get("venue") or "").strip() or None
        starts = parse_event_datetime(request.form.get("starts_at"))
        ends_raw = request.form.get("ends_at")
        ends = parse_event_datetime(ends_raw) if ends_raw else None
        visibility = (request.form.get("visibility") or "school_only").strip()
        event_status = (request.form.get("event_status") or "draft").strip()
        cap = _parse_capacity(request.form.get("capacity"))
        org_id = _parse_org_id(request.form.get("organization_id"))

        now = _now()
        transitioning_to_published = (
            event_status == "published" and row.get("event_status") != "published"
        )
        errors = validate_event_form(
            title,
            description or "",
            venue or "",
            starts,
            ends,
            visibility,
            event_status,
            cap if cap != -1 else None,
            now,
            require_future_start_if_published=transitioning_to_published,
        )
        if cap == -1:
            errors.append("Capacity must be a positive number or empty.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "events/edit.html",
                event=row,
                schools=schools,
                form=request.form,
            )

        if g.current_user.get("role") == "admin":
            try:
                school_id = int(request.form.get("school_id", ""))
            except (TypeError, ValueError):
                flash("Choose a valid school.", "danger")
                return render_template(
                    "events/edit.html",
                    event=row,
                    schools=schools,
                    form=request.form,
                )
        else:
            school_id = int(row["school_id"])

        with db_cursor() as pair:
            if pair is None:
                flash("Cannot reach the database.", "danger")
                return render_template(
                    "events/edit.html",
                    event=row,
                    schools=schools,
                    form=request.form,
                )
            conn, cur = pair
            cur.execute(
                "SELECT 1 FROM schools WHERE school_id = %s AND status = 'active'",
                (school_id,),
            )
            if cur.fetchone() is None:
                flash("Invalid school.", "danger")
                return render_template(
                    "events/edit.html",
                    event=row,
                    schools=schools,
                    form=request.form,
                )
            if org_id:
                cur.execute(
                    """
                    SELECT 1 FROM organizations
                    WHERE organization_id = %s AND school_id = %s AND status = 'active'
                    """,
                    (org_id, school_id),
                )
                if cur.fetchone() is None:
                    org_id = None

            cur.execute(
                """
                UPDATE events SET
                    school_id = %s,
                    organization_id = %s,
                    title = %s,
                    description = %s,
                    location = %s,
                    starts_at = %s,
                    ends_at = %s,
                    visibility = %s,
                    event_status = %s,
                    capacity = %s
                WHERE event_id = %s
                """,
                (
                    school_id,
                    org_id,
                    title,
                    description,
                    venue,
                    starts,
                    ends,
                    visibility,
                    event_status,
                    cap,
                    event_id,
                ),
            )
            conn.commit()

        flash("Event updated.", "success")
        return redirect(url_for("events.event_detail", event_id=event_id))

    return render_template(
        "events/edit.html",
        event=row,
        schools=schools,
        form=None,
    )


@events_bp.route("/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    row = _fetch_event(event_id)
    if not row:
        flash("Event not found.", "warning")
        return redirect(url_for("events.upcoming"))
    if not _can_manage_event(row):
        flash("You cannot delete this event.", "danger")
        return redirect(url_for("events.event_detail", event_id=event_id))

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("events.event_detail", event_id=event_id))
        conn, cur = pair
        cur.execute("DELETE FROM events WHERE event_id = %s", (event_id,))
        conn.commit()

    flash("Event deleted.", "info")
    return redirect(url_for("events.upcoming"))


@events_bp.route("/<int:event_id>/rsvp", methods=["POST"])
@login_required
def rsvp_event(event_id):
    row = _fetch_event(event_id)
    viewer = g.current_user
    if not row or not _can_view_event_detail(row, viewer):
        flash("You cannot RSVP to this event.", "danger")
        return redirect(url_for("events.upcoming"))

    if row.get("event_status") != "published":
        flash("RSVPs are only open for published events.", "warning")
        return redirect(url_for("events.event_detail", event_id=event_id))

    starts = row.get("starts_at")
    if starts:
        st = starts.replace(tzinfo=None) if hasattr(starts, "replace") and getattr(starts, "tzinfo", None) else starts
        if st < _now():
            flash("This event has already started.", "warning")
            return redirect(url_for("events.event_detail", event_id=event_id))

    action = (request.form.get("action") or "join").strip().lower()
    uid = int(viewer["user_id"])
    eid = int(event_id)

    with db_cursor() as pair:
        if pair is None:
            flash("Cannot reach the database.", "danger")
            return redirect(url_for("events.event_detail", event_id=event_id))
        conn, cur = pair

        if action == "leave":
            cur.execute(
                "DELETE FROM event_rsvps WHERE event_id = %s AND user_id = %s",
                (eid, uid),
            )
            conn.commit()
            flash("You are no longer attending.", "info")
            return redirect(url_for("events.event_detail", event_id=event_id))

        cur.execute(
            """
            SELECT COUNT(*) AS c FROM event_rsvps
            WHERE event_id = %s AND status = 'going'
            """,
            (eid,),
        )
        going = int(cur.fetchone()["c"])
        capacity = row.get("capacity")
        cur.execute(
            "SELECT status FROM event_rsvps WHERE event_id = %s AND user_id = %s",
            (eid, uid),
        )
        existing = cur.fetchone()

        status = "going"
        if capacity is not None and going >= int(capacity):
            if not (existing and existing.get("status") == "going"):
                status = "waitlist"

        if existing:
            cur.execute(
                """
                UPDATE event_rsvps SET status = %s
                WHERE event_id = %s AND user_id = %s
                """,
                (status, eid, uid),
            )
        else:
            cur.execute(
                """
                INSERT INTO event_rsvps (event_id, user_id, status)
                VALUES (%s, %s, %s)
                """,
                (eid, uid, status),
            )
        conn.commit()

    if status == "waitlist":
        flash("Event is full — you were added to the waitlist.", "warning")
    else:
        flash("You are attending this event.", "success")
    return redirect(url_for("events.event_detail", event_id=event_id))
