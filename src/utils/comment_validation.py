def validate_comment_content(raw):
    if raw is None:
        return "Comment cannot be empty."
    text = raw.strip()
    if not text:
        return "Comment cannot be empty."
    if len(text) > 2000:
        return "Comment must be at most 2,000 characters."
    return None
