"""
Secure file storage for attachments (Sprint 23).

Security properties:
- Files are saved under a private directory that is never mounted as static
  content — there is no public URL for any file, ever.
- The on-disk filename is a random UUID, not the user-supplied filename, so
  there's no path traversal via the original filename and no collisions.
- The original filename is preserved only as metadata (for the download's
  Content-Disposition header), never used to build a filesystem path.
- Downloads only happen through the authenticated /attachments/{id}/download
  endpoint, which re-checks entity access before streaming bytes.
"""
from __future__ import annotations

import uuid
from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "private_uploads"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def save_file(file_bytes: bytes, original_filename: str) -> str:
    """Writes file_bytes under a random name and returns the storage_path
    to persist on the Attachment row. Never derives the path from user input."""
    extension = Path(original_filename).suffix[:20]  # cap extension length defensively
    safe_name = f"{uuid.uuid4()}{extension}"
    dest = STORAGE_ROOT / safe_name
    dest.write_bytes(file_bytes)
    return str(dest)


def read_file(storage_path: str) -> bytes:
    path = Path(storage_path)
    # Defensive: never read outside the storage root, even if a storage_path
    # were somehow tampered with before reaching here.
    if STORAGE_ROOT not in path.resolve().parents and path.resolve() != STORAGE_ROOT:
        raise ValueError("Refusing to read a path outside the attachment storage root")
    return path.read_bytes()


def delete_file(storage_path: str) -> None:
    path = Path(storage_path)
    if path.exists() and (STORAGE_ROOT in path.resolve().parents):
        path.unlink()
