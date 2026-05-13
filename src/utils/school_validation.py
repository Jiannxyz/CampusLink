import re

SCHOOL_CODE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{2,30}$")
EMAIL_DOMAIN_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$"
)
LOGO_PATH_PATTERN = re.compile(r"^[\w./\-]{0,500}$")
LOGO_URL_PATTERN = re.compile(r"^https?://[^\s]{1,500}$")


def validate_school_form(
    name,
    school_code,
    email_domain,
    campus,
    city,
    province,
    country,
    description,
    logo_path,
    status,
):
    errors = []
    if not name or not name.strip() or len(name) > 150:
        errors.append("School name is required (max 150 characters).")
    if not school_code or not SCHOOL_CODE_PATTERN.match(school_code.strip()):
        errors.append(
            "School code is required: 2–30 letters, numbers, hyphens, or underscores."
        )
    if not email_domain or len(email_domain) > 120:
        errors.append("Email domain is required (max 120 characters).")
    elif not EMAIL_DOMAIN_PATTERN.match(email_domain.strip().lower()):
        errors.append("Enter a valid email domain (e.g. stateu.edu).")
    if campus and len(campus) > 150:
        errors.append("Campus must be at most 150 characters.")
    if city and len(city) > 100:
        errors.append("City must be at most 100 characters.")
    if province and len(province) > 100:
        errors.append("Province must be at most 100 characters.")
    if country and len(country) > 100:
        errors.append("Country must be at most 100 characters.")
    if description and len(description) > 10000:
        errors.append("Description is too long (max 10,000 characters).")
    if logo_path:
        lp = logo_path.strip()
        if len(lp) > 500:
            errors.append("Logo URL or path must be at most 500 characters.")
        elif lp.startswith(("http://", "https://")):
            if not LOGO_URL_PATTERN.match(lp):
                errors.append("Enter a valid http(s) logo URL.")
        elif not LOGO_PATH_PATTERN.match(lp):
            errors.append(
                "Logo path must use only letters, numbers, and ./-_ (relative to /static), "
                "or use a full http(s) URL."
            )
    if status not in ("active", "inactive"):
        errors.append("Status must be active or inactive.")
    return errors
