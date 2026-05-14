import os
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})
MAX_IMAGE_BYTES = 3 * 1024 * 1024


def extension_allowed(filename):
    if not filename or "." not in filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def save_user_image(file_storage, user_id, static_folder, subdir="uploads/profiles"):
    """
    Save an uploaded image under static/<subdir>/.
    Returns relative path for static url_for('static', filename=...) or None on skip/fail.
    """
    fn = (getattr(file_storage, "filename", None) or "").strip()
    if not file_storage or not fn:
        return None
    if not extension_allowed(fn):
        raise ValueError("Image must be PNG, JPG, JPEG, WebP, or GIF.")
    try:
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
    except OSError:
        size = 0
    file_storage.seek(0)
    if size > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 3 MB or smaller.")
    if size == 0:
        return None

    ext = Path(secure_filename(fn)).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".jpg"
    name = f"{int(user_id)}_{uuid.uuid4().hex[:10]}{ext}"
    dest_dir = Path(static_folder) / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / name
    try:
        file_storage.seek(0)
    except OSError:
        pass
    file_storage.save(str(dest_path))
    return f"{subdir}/{name}".replace("\\", "/")


def delete_old_upload(static_folder, relative_path):
    if not relative_path or str(relative_path).startswith("http"):
        return
    try:
        p = Path(static_folder) / str(relative_path).lstrip("/")
        if p.is_file() and "uploads/profiles" in str(p):
            p.unlink()
    except OSError:
        pass
