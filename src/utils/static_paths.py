"""Normalize stored static paths and build public URLs for templates."""


def normalize_static_path(raw):
    """
    Return a path suitable for url_for('static', filename=...), an http(s) URL, or None.
    Strips leading slashes and a /static/ prefix when present.
    """
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/static/"):
        s = s[len("/static/") :]
    return s.lstrip("/")


def media_public_url(path, static_url_for):
    """Resolve DB path or external URL to a browser-ready src."""
    normalized = normalize_static_path(path)
    if not normalized:
        return None
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return normalized
    return static_url_for("static", filename=normalized)
