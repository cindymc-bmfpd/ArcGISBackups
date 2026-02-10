"""
ArcGIS Online Backup App – Flask backend.
Login, resolve items (by ID or search), and run OfflineContentManager.export_items.
"""
import json
import os
import re
import shutil
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")

# #region agent log
def _debug_log(message: str, data: dict, hypothesis_id: str = "server_side_sessions") -> None:
    try:
        with open(Path(__file__).resolve().parent / ".cursor" / "debug.log", "a") as f:
            f.write(json.dumps({"location": "app.py", "message": message, "data": data, "hypothesisId": hypothesis_id}) + "\n")
    except Exception:
        pass
# #endregion

# Server-side session: data stored on server, only session ID in cookie (avoids 4KB limit)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = str(Path(__file__).resolve().parent / "flask_session")
Session(app)
# Clear session store on startup so each run starts with no persisted session.
try:
    session_dir = Path(app.config["SESSION_FILE_DIR"])
    if session_dir.exists():
        shutil.rmtree(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
# #region agent log
_debug_log("server_side_sessions_enabled", {"session_type": app.config["SESSION_TYPE"]})
# #endregion

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


def get_gis():
    """Build a GIS connection from session (url, username, password). Returns None if not logged in."""
    if not session.get("logged_in"):
        return None
    url = session.get("gis_url") or DEFAULT_AGO_URL
    username = session.get("username")
    password = session.get("password")
    if not username or not password:
        return None
    try:
        from arcgis.gis import GIS
        return GIS(url, username, password)
    except Exception:
        return None


def normalize_item_ids(raw: str) -> list[str]:
    """Parse comma- or newline-separated item IDs; return list of non-empty stripped IDs."""
    if not raw or not raw.strip():
        return []
    parts = re.split(r"[\s,\n]+", raw.strip())
    return [p.strip() for p in parts if p.strip()]


def resolve_items_by_ids(gis, item_ids: list[str]) -> tuple[list, list]:
    """Resolve item IDs to Item objects. Returns (items, invalid_ids)."""
    from arcgis.gis import Item
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


@app.route("/", methods=["GET", "POST"])
def index():
    """Serve the single-page UI and handle no-op POST (e.g. form reload)."""
    if request.method == "POST":
        if request.form.get("action") == "login":
            return redirect(url_for("login"))
        if request.form.get("action") == "search":
            return redirect(url_for("search"))
        if request.form.get("action") == "backup":
            return redirect(url_for("backup"))

    session_message = (session.pop("message", None), session.pop("message_type", "info"))
    search_results = session.pop("search_results", None)
    last_content_folder = session.get("last_content_folder") or ""
    last_item_type = session.get("last_item_type") or ""

    # Load user content folders (ArcGIS Online) for folder-scoped search.
    user_folders: list[dict] = []
    if session.get("logged_in"):
        gis = get_gis()
        if gis is not None:
            user_folders = get_user_folders(gis)

    return render_template(
        "index.html",
        logged_in=session.get("logged_in", False),
        gis_url=session.get("gis_url", DEFAULT_AGO_URL),
        username=session.get("username", ""),
        default_ago_url=DEFAULT_AGO_URL,
        search_item_types=SEARCH_ITEM_TYPES,
        backup_base_path=BACKUP_BASE_PATH,
        session_message=session_message,
        search_results=search_results or [],
        user_folders=user_folders,
        last_content_folder=last_content_folder,
        last_item_type=last_item_type,
    )


@app.route("/login", methods=["POST"])
def login():
    """Validate credentials with ArcGIS and store minimal session."""
    url = (request.form.get("gis_url") or "").strip() or DEFAULT_AGO_URL
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not username or not password:
        session["message"] = "Username and password are required."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    try:
        from arcgis.gis import GIS
        gis = GIS(url, username, password)
        # Trigger a simple read to verify connection
        _ = gis.users.me
    except Exception as e:
        session["message"] = f"Login failed: {e}"
        session["message_type"] = "error"
        return redirect(url_for("index"))

    session["logged_in"] = True
    session["gis_url"] = url
    session["username"] = username
    session["password"] = password  # in-memory for session only; see README
    session["message"] = f"Logged in as {username}."
    session["message_type"] = "success"
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    """Clear session (including password)."""
    session.clear()
    session["message"] = "Logged out."
    session["message_type"] = "success"
    return redirect(url_for("index"))


@app.route("/search", methods=["POST"])
def search():
    """Search user content by item type; return same page with search results."""
    if not session.get("logged_in"):
        session["message"] = "Please log in first."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    item_type = (request.form.get("item_type") or "").strip()
    if not item_type:
        session["message"] = "Select an item type to search."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    # Optional: restrict search to a specific ArcGIS content folder.
    folder_id = (request.form.get("content_folder") or "").strip()

    gis = get_gis()
    if gis is None:
        session["message"] = "Session invalid. Please log in again."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    def _matches_item_type(item, selected_type: str) -> bool:
        """Return True if item.type matches the selected item type filter."""
        actual_type = getattr(item, "type", "") or ""
        if selected_type == "Map":
            # Treat "Map" as Web Map and Web Mapping Application.
            return actual_type in ("Web Map", "Web Mapping Application")
        return actual_type == selected_type

    try:
        if not folder_id:
            # Current behavior: search across all content by item type.
            results = gis.content.search(query="*", item_type=item_type, max_items=100)
        else:
            # Folder-scoped search: get items from the selected folder and filter by type.
            me = gis.users.me
            folder_items = me.items(folder=folder_id)
            filtered = [item for item in folder_items if _matches_item_type(item, item_type)]
            results = filtered[:100]
    except Exception as e:
        session["message"] = f"Search failed: {e}"
        session["message_type"] = "error"
        return redirect(url_for("index"))

    session["message"] = f"Found {len(results)} item(s)."
    session["message_type"] = "success"
    session["search_results"] = [
        {"id": item.id, "title": item.title, "type": getattr(item, "type", "")}
        for item in results
    ]
    session["last_content_folder"] = folder_id
    session["last_item_type"] = item_type
    # #region agent log
    _debug_log("search_results_stored_in_session", {"count": len(results)}, "server_side_sessions")
    # #endregion
    return redirect(url_for("index"))


@app.route("/backup", methods=["POST"])
def backup():
    """Resolve item IDs, validate path, run OfflineContentManager.export_items."""
    if not session.get("logged_in"):
        session["message"] = "Please log in first."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    gis = get_gis()
    if gis is None:
        session["message"] = "Session invalid. Please log in again."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    raw_ids = request.form.get("item_ids") or ""
    backup_path_input = (request.form.get("backup_path") or "").strip()

    item_ids = normalize_item_ids(raw_ids)
    if not item_ids:
        session["message"] = "Enter at least one item ID to back up."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    path_obj = safe_backup_path(backup_path_input)
    if path_obj is None:
        session["message"] = "Invalid backup path: must be under the allowed base directory."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    items, invalid_ids = resolve_items_by_ids(gis, item_ids)
    if invalid_ids:
        session["message"] = f"Invalid or inaccessible item IDs: {', '.join(invalid_ids)}"
        session["message_type"] = "error"
        return redirect(url_for("index"))

    if not items:
        session["message"] = "No valid items to back up."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    path_str = str(path_obj)
    try:
        path_obj.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        session["message"] = f"Cannot create backup directory: {e}"
        session["message_type"] = "error"
        return redirect(url_for("index"))

    try:
        ocm = gis.content.offline
        result = ocm.export_items(items, path_str)
        out_path = getattr(result, "path", path_str) or path_str
        session["message"] = f"Backup completed. Output saved in: {out_path}"
        session["message_type"] = "success"
    except Exception as e:
        session["message"] = f"Export failed: {e}"
        session["message_type"] = "error"

    return redirect(url_for("index"))




if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
