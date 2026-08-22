"""File utilities"""
import os
from pathlib import Path


def ensure_dir(path: str) -> None:
    """Ensure directory exists"""
    os.makedirs(path, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lstrip('.').lower()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks"""
    # Remove path separators and special characters
    filename = os.path.basename(filename)
    # Keep only alphanumeric, dots, dashes, underscores
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    sanitized = "".join(c for c in filename if c in allowed_chars)
    return sanitized or "file"
