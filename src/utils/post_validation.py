import re

ALLOWED_CATEGORIES = frozenset(
    ("general", "academic", "events", "clubs", "questions", "marketplace")
)
ALLOWED_PRIVACY = frozenset(
    ("public", "school_only", "followers_only", "private")
)

LOGO_PATH_PATTERN = re.compile(r"^[\w./\-]{0,500}$")
IMAGE_URL_PATTERN = re.compile(r"^https?://[^\s]{1,500}$")


def validate_post_form(title, content, image_path, category, privacy):
    errors = []
    if not title or not title.strip():
        errors.append("Title is required.")
    elif len(title) > 200:
        errors.append("Title must be at most 200 characters.")
    if not content or not content.strip():
        errors.append("Content is required.")
    elif len(content) > 20000:
        errors.append("Content is too long (max 20,000 characters).")
    if image_path:
        lp = image_path.strip()
        if len(lp) > 500:
            errors.append("Image URL or path must be at most 500 characters.")
        elif lp.startswith(("http://", "https://")):
            if not IMAGE_URL_PATTERN.match(lp):
                errors.append("Enter a valid http(s) image URL.")
        elif not LOGO_PATH_PATTERN.match(lp):
            errors.append(
                "Image path must use only letters, numbers, and ./-_ (relative to /static), "
                "or use a full http(s) URL."
            )
    if category not in ALLOWED_CATEGORIES:
        errors.append("Choose a valid category.")
    if privacy not in ALLOWED_PRIVACY:
        errors.append("Choose a valid audience.")
    return errors
