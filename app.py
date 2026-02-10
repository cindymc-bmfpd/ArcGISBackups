"""
ArcGIS Online Backup – shared library.
Constants and helpers for folders, items, paths, and export.
Used by backup_cli.py (main application).
"""
import os
import re
from pathlib import Path

# Base directory for backups; user path is resolved relative to this.
BACKUP_BASE_PATH = os.path.abspath(os.environ.get("BACKUP_BASE_PATH", "./backups"))

# Default ArcGIS Online URL
DEFAULT_AGO_URL = "https://www.arcgis.com"

# Item types for "layers and maps" search
SEARCH_ITEM_TYPES = [
    ("Feature Service", "Feature Service"),
    ("Web Map", "Web Map"),
    ("Map", "Web Map and Web Mapping Application"),
]


def get_user_folders(gis) -> list[dict]:
    """
    Return a list of user content folder dicts for the given GIS.
    Each dict has "id" and "title" (title may be derived from id or str(f) if missing).
    """
    user_folders: list[dict] = []
    try:
        me = gis.users.me
        raw = getattr(me, "folders", []) or []
        folders = list(raw)
        for f in folders:
            if isinstance(f, dict):
                fid = f.get("id") or f.get("folderId") or f.get("title") or f.get("name")
                title = f.get("title") or f.get("name") or f.get("folderName") or fid
            else:
                fid = (
                    getattr(f, "id", None) or getattr(f, "folderId", None)
                    or getattr(f, "title", None) or getattr(f, "name", None)
                )
                title = (
                    getattr(f, "title", None) or getattr(f, "name", None)
                    or getattr(f, "folderName", None) or fid
                )
            display = title or fid or str(f)
            if fid or display:
                user_folders.append({"id": str(fid) if fid else "", "title": str(display)})
    except Exception:
        pass
    return user_folders


def get_backuppable_items_in_folder(gis, folder_id: str) -> list:
    """Return list of Item objects in folder that are Feature Service or Web Map."""
    me = gis.users.me
    folder_items = me.items(folder=folder_id)
    return [
        i
        for i in folder_items
        if getattr(i, "type", "") in ("Feature Service", "Web Map", "Web Mapping Application")
    ][:100]


def normalize_item_ids(raw: str) -> list[str]:
    """Parse comma- or newline-separated item IDs; return list of non-empty stripped IDs."""
    if not raw or not raw.strip():
        return []
    parts = re.split(r"[\s,\n]+", raw.strip())
    return [p.strip() for p in parts if p.strip()]


def resolve_items_by_ids(gis, item_ids: list[str]) -> tuple[list, list]:
    """Resolve item IDs to Item objects. Returns (items, invalid_ids)."""
    items = []
    invalid_ids = []
    for iid in item_ids:
        try:
            item = gis.content.get(iid)
            if item is None:
                invalid_ids.append(iid)
            else:
                items.append(item)
        except Exception:
            invalid_ids.append(iid)
    return items, invalid_ids


def safe_backup_path(user_path: str) -> Path | None:
    """
    Resolve user-provided path to an absolute path under BACKUP_BASE_PATH.
    Returns None if path would escape the base (path traversal).
    """
    base = Path(BACKUP_BASE_PATH).resolve()
    base.mkdir(parents=True, exist_ok=True)
    if not user_path or not user_path.strip():
        return base
    # Join with base and resolve to detect traversal
    combined = (base / user_path.strip()).resolve()
    try:
        combined.relative_to(base)
    except ValueError:
        return None
    return combined
