"""
ArcGIS Online Backup – shared library.
Constants and helpers for folders, items, paths, and export.
Used by backup_cli.py (main application).
"""
import os
import re
from datetime import datetime
from pathlib import Path

# Base directory for backups; user path is resolved relative to this.
BACKUP_BASE_PATH = os.path.abspath(os.environ.get("BACKUP_BASE_PATH", "."))

# Default ArcGIS Online URL
DEFAULT_AGO_URL = "https://www.arcgis.com"

# Default path for credentials file (relative to project root)
DEFAULT_CREDENTIALS_FILE = Path(__file__).resolve().parent / ".arcgis_credentials"

# Keys expected in credentials file (name=value format)
USERNAME = "USERNAME"
PASSWORD = "PASSWORD"


def load_credentials_from_file(filepath: Path | str | None = None) -> tuple[str, str] | None:
    """
    Read username and password from a credentials file.
    File format: USERNAME=foo and PASSWORD=bar (one per line).
    Returns (username, password) if successful, None if file missing or malformed.
    """
    path = Path(filepath) if filepath else DEFAULT_CREDENTIALS_FILE
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        pairs: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
            if match:
                key, value = match.group(1), match.group(2).strip()
                pairs[key] = value
        if USERNAME not in pairs or PASSWORD not in pairs:
            return None
        return pairs[USERNAME], pairs[PASSWORD]
    except (OSError, IOError):
        return None


def default_backup_subpath(
    folder_title: str,
    items: list[tuple[str, str]],
    now: datetime | None = None,
) -> str:
    """
    Build default backup subpath: YYYYMONDD/Folder/type/name.
    Each item is (name, type) e.g. ("My Map", "Web Map") -> "WebMap/My Map".
    Type has spaces removed (Web Map -> WebMap). Sanitizes for filesystem use.
    """
    def _sanitize(s: str) -> str:
        return re.sub(r'[/\\:*?"<>|]', "_", s or "").strip() or "unnamed"

    def _type_key(t: str) -> str:
        return re.sub(r"\s+", "", (t or "").strip()) or "Item"

    dt = now or datetime.now()
    current_date = f"{dt:%Y}{dt:%b}".upper() + f"{dt:%d}"
    parts = [
        f"{_type_key(item_type)}/{_sanitize(name)}"
        for name, item_type in items
    ]
    item_part = "_".join(parts) if parts else "unnamed"
    return f"{current_date}/{_sanitize(folder_title)}/{item_part}"


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
    Returns None if the resolved path escapes the base directory (prevents path traversal).
    """
    base = Path(BACKUP_BASE_PATH).resolve()
    base.mkdir(parents=True, exist_ok=True)

    if not user_path or not user_path.strip():
        return base

    candidate = (base / user_path.strip()).resolve()
    if base in candidate.parents or candidate == base:
        return candidate
    return None
