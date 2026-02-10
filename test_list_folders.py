"""
CLI test script: log in to ArcGIS the same way as app.py and list all user content folders.
Run: python test_list_folders.py
"""
import getpass
import os

from app import DEFAULT_AGO_URL, get_user_folders


def main() -> None:
    # URL: env AGO_URL or prompt (blank = default)
    url = (os.environ.get("AGO_URL") or "").strip()
    if not url:
        url = input("ArcGIS URL (blank for default): ").strip() or DEFAULT_AGO_URL
    username = input("Username: ").strip()
    if not username:
        print("Username is required.")
        return
    password = getpass.getpass("Password: ")
    if not password:
        print("Password is required.")
        return

    try:
        from arcgis.gis import GIS
        gis = GIS(url, username, password)
        me = gis.users.me
        print(f"Logged in as {me.username} to {gis.properties.portalName}")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # List folders using shared logic from app.py
    folders = get_user_folders(gis)
    if not folders:
        print("No folders found.")
        return
    print(f"\nFolders ({len(folders)}):")
    for folder in folders:
        title = folder.get("title") or ""
        fid = folder.get("id") or ""
        print(f"  {title}" + (f"  (id={fid})" if fid else ""))


if __name__ == "__main__":
    main()
