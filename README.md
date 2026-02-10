# ArcGIS Online Backup App

A simple web app to log into your ArcGIS Online account and back up specified layers and maps. Uses the [ArcGIS API for Python](https://developers.arcgis.com/python/latest/guide/install-and-set-up/) and Esri’s **OfflineContentManager** to export items (and their dependencies) to a compressed package on disk.

This is a work in progress and is not yet functional.  Here's a list of TODO:

    [] Logging in with credentials via UI works, but takes several attempts with MFA
    [] Listing contents of selected folders doesn't work

**Requirements:** Python 3.10–3.12 (see [ArcGIS API for Python system requirements](https://developers.arcgis.com/python/guide/system-requirements/)).

## Create the Environment

From your project directory

    python3 -m venv venv
    source venv/bin/activate

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

## CLI backup (no UI)

You can run a command-line backup that prompts for credentials and lets you pick a folder and item(s) to back up:

```bash
python backup_cli.py
```

1. Enter ArcGIS URL (or leave blank for default), username, and password.
2. Choose a folder from the numbered list.
3. Choose one or more layers/maps by number (e.g. `1` or `1,3,5`).
4. Enter an optional backup subpath (or leave blank for the base backup directory).
5. The export runs and prints the output path when done.

The same `BACKUP_BASE_PATH` environment variable applies; the subpath you enter is under that base.

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

## Tests

Tests verify that Search results correctly populate the Item IDs list (backend rendering and Add-selected behavior).

```bash
pip install -r requirements-dev.txt
pytest tests/test_search_item_ids.py -v
```

- **Backend:** After login and search, the index page renders checkboxes with `data-id` and the "Add selected to backup list" button; backup form receives and parses `item_ids` correctly.
- **Add-selected logic:** Merge/dedupe of selected IDs with existing textarea value is tested (same behavior as the front-end script).
- **E2E (optional):** With Playwright installed (`playwright install chromium`), one test runs the real JavaScript in a headless browser to confirm the textarea is populated when "Add selected" is clicked.

## Optional: ArcGIS Enterprise

If you use ArcGIS Enterprise instead of ArcGIS Online, set the **ArcGIS URL** to your portal URL (e.g. `https://gis.yourorg.com/portal`) and log in with your portal username and password.
