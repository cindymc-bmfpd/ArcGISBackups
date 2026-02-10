# ArcGIS Online Backup App

A simple web app to log into your ArcGIS Online account and back up specified layers and maps. Uses the [ArcGIS API for Python](https://developers.arcgis.com/python/latest/guide/install-and-set-up/) and Esri’s **OfflineContentManager** to export items (and their dependencies) to a compressed package on disk.

This is a work in progress and is not yet functional.  Here's a list of TODO:

    [] Logging in with credentials via UI works, but takes several attempts with MFA
    [] Listing contents of selected folders doesn't work

**Requirements:** Python 3.10–3.12 (see [ArcGIS API for Python system requirements](https://developers.arcgis.com/python/guide/system-requirements/)).

## Install

```bash
pip install -r requirements.txt
```

## Run

From the project directory:

```bash
export FLASK_APP=app.py
flask run
```

Or run the app directly:

```bash
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Usage

1. **Log in** – Enter your ArcGIS Online URL (default `https://www.arcgis.com`), username, and password. For ArcGIS Enterprise, use your portal URL (e.g. `https://yourorg.com/portal`).
2. **Backup folder** – Optionally enter a subfolder name. All backups are stored under a single base directory (see below).
3. **Item IDs** – Paste one or more item IDs (comma- or newline-separated), or use **Search my content** to find Feature Services or Web Maps and add them to the list.
4. **Run backup** – Click **Run backup**. The export may take a few minutes. When it finishes, the backup package path is shown on the page.

Backups are written to the folder you chose (or the base directory if left empty). The exact output name/form is determined by the ArcGIS API (compressed package under that path).

## Backup base path

By default, backups are saved under `./backups` (relative to the directory from which you run the app). To use another base directory, set the environment variable:

```bash
export BACKUP_BASE_PATH=/path/to/your/backups
flask run
```

The path you enter in the UI is a **subpath** under this base (e.g. `2025-02`). It cannot escape the base directory (path traversal is blocked).

## Security

- Use this app only in a **trusted environment** (e.g. on your own machine).
- Credentials are kept in the session for the duration of your login and are not stored on disk. The app is intended for local use at `http://127.0.0.1:5000`.
- For production or shared use, set `FLASK_SECRET_KEY` and consider HTTPS and secure cookie options.

## Optional: ArcGIS Enterprise

If you use ArcGIS Enterprise instead of ArcGIS Online, set the **ArcGIS URL** to your portal URL (e.g. `https://gis.yourorg.com/portal`) and log in with your portal username and password.
