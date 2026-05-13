from datetime import datetime

ALLOWED_VISIBILITY = frozenset(("public", "school_only", "organization_only"))
ALLOWED_EVENT_STATUS = frozenset(("draft", "published", "cancelled", "completed"))


def parse_event_datetime(raw):
    """Parse HTML datetime-local or common MySQL/datetime strings."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    normalized = s.replace("T", " ", 1)
    if len(normalized) == 16 and normalized.count(":") == 1:
        normalized = normalized + ":00"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(normalized[:19], fmt)
        except ValueError:
            continue
    return None


def validate_event_form(
    title,
    description,
    venue,
    starts_at,
    ends_at,
    visibility,
    event_status,
    capacity,
    now,
    require_future_start_if_published,
):
    errors = []
    if not title or not str(title).strip():
        errors.append("Event title is required.")
    elif len(title) > 180:
        errors.append("Title must be at most 180 characters.")
    if description is not None and len(description) > 50000:
        errors.append("Description is too long.")
    if venue and len(venue) > 200:
        errors.append("Venue must be at most 200 characters.")
    if starts_at is None:
        errors.append("Start date and time are required.")
    if ends_at is not None and starts_at is not None and ends_at < starts_at:
        errors.append("End time must be on or after the start time.")
    if visibility not in ALLOWED_VISIBILITY:
        errors.append("Choose a valid visibility option.")
    if event_status not in ALLOWED_EVENT_STATUS:
        errors.append("Choose a valid event status.")
    if capacity is not None:
        if capacity < 1 or capacity > 100000:
            errors.append("Capacity must be between 1 and 100,000, or left empty.")
    if (
        require_future_start_if_published
        and event_status == "published"
        and starts_at is not None
        and starts_at < now
    ):
        errors.append("Published events must have a start time in the future.")
    return errors
