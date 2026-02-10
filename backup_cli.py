"""
CLI backup app: prompt for credentials, choose folder and item(s), then export.
Run from project directory: python backup_cli.py
"""
import getpass
import os
import sys

from app import (
    BACKUP_BASE_PATH,
    DEFAULT_AGO_URL,
    get_backuppable_items_in_folder,
    get_user_folders,
    safe_backup_path,
)


def main() -> None:
    # Credentials
    url = (os.environ.get("AGO_URL") or "").strip()
    if not url:
        url = input("ArcGIS URL (blank for default): ").strip() or DEFAULT_AGO_URL
    username = input("Username: ").strip()
    if not username:
        print("Username is required.")
        sys.exit(1)
    password = getpass.getpass("Password: ")
    if not password:
        print("Password is required.")
        sys.exit(1)

    # Login
    try:
        from arcgis.gis import GIS

        gis = GIS(url, username, password)
        me = gis.users.me
        print(f"Logged in as {me.username} to {gis.properties.portalName}")
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    # Folders
    folders = get_user_folders(gis)
    if not folders:
        print("No folders found.")
        sys.exit(1)

    print("\nFolders:")
    for i, folder in enumerate(folders, 1):
        title = folder.get("title") or folder.get("id") or "(unnamed)"
        print(f"  {i}. {title}")

    folder_choice = input("\nEnter folder number: ").strip()
    try:
        idx = int(folder_choice)
    except ValueError:
        print("Invalid number.")
        sys.exit(1)
    if idx < 1 or idx > len(folders):
        print("Number out of range.")
        sys.exit(1)
    folder_id = folders[idx - 1].get("id") or ""
    folder_title = folders[idx - 1].get("title") or folder_id

    # Items in folder
    try:
        items = get_backuppable_items_in_folder(gis, folder_id)
    except Exception as e:
        print(f"Failed to list items in folder: {e}")
        sys.exit(1)

    if not items:
        print(f"No layers or maps found in '{folder_title}'.")
        sys.exit(1)

    print(f"\nLayers and maps in '{folder_title}':")
    for i, item in enumerate(items, 1):
        title = getattr(item, "title", "") or getattr(item, "id", "") or "(unnamed)"
        itype = getattr(item, "type", "") or ""
        print(f"  {i}. {title}  ({itype})")

    choice_str = input("\nEnter item number(s), e.g. 1 or 1,3,5: ").strip()
    indices = []
    for part in choice_str.replace(" ", "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
            if 1 <= n <= len(items):
                indices.append(n - 1)
            else:
                print(f"Number {n} out of range (1–{len(items)}).")
                sys.exit(1)
        except ValueError:
            print(f"Invalid number: {part}")
            sys.exit(1)

    if not indices:
        print("No items selected.")
        sys.exit(1)

    selected = [items[i] for i in sorted(set(indices))]

    # Backup path
    user_path = input("\nBackup subpath (blank for base): ").strip()
    path_obj = safe_backup_path(user_path)
    if path_obj is None:
        print("Invalid backup path: must be under the allowed base directory.")
        sys.exit(1)
    path_str = str(path_obj)

    try:
        path_obj.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Cannot create backup directory: {e}")
        sys.exit(1)

    # Export
    print("\nExporting...")
    try:
        ocm = gis.content.offline
        result = ocm.export_items(selected, path_str)
        out_path = getattr(result, "path", path_str) or path_str
        print(f"Backup completed. Output saved in: {out_path}")
    except Exception as e:
        print(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
