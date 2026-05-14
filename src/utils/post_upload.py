"""Secure post image uploads (gallery)."""

from __future__ import annotations

import os
import uuid
from typing import List, Tuple

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_BYTES = 8 * 1024 * 1024  # 8 MiB per file
MAX_FILES = 8


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def save_post_images(
    files: List[FileStorage],
    upload_folder: str,
    *,
    max_files: int = MAX_FILES,
) -> Tuple[List[str], List[str]]:
    """
    Save uploaded images to upload_folder. Returns (saved_relative_paths, errors).
    Paths are relative to static/ (e.g. uploads/posts/xxx.jpg).
    """
    errors: List[str] = []
    saved: List[str] = []

    if not files:
        return saved, errors

    os.makedirs(upload_folder, exist_ok=True)

    for i, file in enumerate(files[:max_files]):
        if not file or not getattr(file, "filename", None):
            continue
        if not allowed_file(file.filename):
            errors.append(f"File {i + 1}: only JPG, JPEG, PNG, or WEBP allowed.")
            continue
        original = secure_filename(file.filename)
        ext = original.rsplit(".", 1)[1].lower() if "." in original else "jpg"
        if ext not in ALLOWED_EXTENSIONS:
            ext = "jpg"
        unique = f"{uuid.uuid4().hex}.{ext}"
        dest = os.path.join(upload_folder, unique)
        file.save(dest)
        try:
            size = os.path.getsize(dest)
        except OSError:
            size = 0
        if size > MAX_FILE_BYTES:
            try:
                os.remove(dest)
            except OSError:
                pass
            errors.append(f"File {i + 1}: must be {MAX_FILE_BYTES // (1024 * 1024)} MB or smaller.")
            continue
        rel = os.path.join("uploads", "posts", unique).replace("\\", "/")
        saved.append(rel)

    return saved, errors
