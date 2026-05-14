import re

from utils.validation import validate_email, validate_name, validate_password, validate_username

BIO_MAX = 300


def validate_bio(bio):
    if bio is None:
        return None
    s = str(bio).strip()
    if len(s) > BIO_MAX:
        return f"Bio must be at most {BIO_MAX} characters."
    return None


def validate_optional_url(raw, field_label, max_len=300):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if len(s) > max_len:
        return f"{field_label} is too long (max {max_len} characters)."
    if not re.match(r"^https?://", s, re.I):
        return f"{field_label} must start with http:// or https://"
    return None


def validate_profile_form(
    first_name,
    last_name,
    username,
    email,
    bio,
    website,
    twitter,
    linkedin,
    new_password,
    confirm_password,
):
    errors = []
    for fn in (
        lambda: validate_name(first_name, last_name),
        lambda: validate_username(username),
        lambda: validate_email(email),
        lambda: validate_bio(bio),
        lambda: validate_optional_url(website, "Website link", 300),
        lambda: validate_optional_url(twitter, "Twitter/X link", 200),
        lambda: validate_optional_url(linkedin, "LinkedIn link", 300),
    ):
        e = fn()
        if e:
            errors.append(e)

    if new_password or confirm_password:
        if new_password != confirm_password:
            errors.append("New passwords do not match.")
        else:
            pe = validate_password(new_password)
            if pe:
                errors.append(pe)

    return errors
