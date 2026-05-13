import re

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,50}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_username(username):
    if not username or not USERNAME_PATTERN.match(username.strip()):
        return "Username must be 3–50 characters and use only letters, numbers, or underscores."
    return None


def validate_email(email):
    if not email or len(email) > 120:
        return "Email is required (max 120 characters)."
    if not EMAIL_PATTERN.match(email.strip().lower()):
        return "Enter a valid email address."
    return None


def validate_password(password):
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password is too long."
    return None


def validate_name(first_name, last_name):
    if not first_name or len(first_name.strip()) < 1 or len(first_name) > 80:
        return "First name is required (max 80 characters)."
    if not last_name or len(last_name.strip()) < 1 or len(last_name) > 80:
        return "Last name is required (max 80 characters)."
    return None
