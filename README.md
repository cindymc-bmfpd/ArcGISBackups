# ArcGIS Online Backup

A command-line app to log into your ArcGIS Online account and back up selected layers and maps. Uses the [ArcGIS API for Python](https://developers.arcgis.com/python/latest/guide/install-and-set-up/) and Esri’s **OfflineContentManager** to export items (and their dependencies) to a compressed package on disk.

**Requirements:** Python 3.10–3.12 (see [ArcGIS API for Python system requirements](https://developers.arcgis.com/python/guide/system-requirements/)).

## Create the environment

From your project directory:

```bash
python3 -m venv venv
source venv/bin/activate
```

## Install

```bash
pip install -r requirements.txt
```

## Run (main application)

From the project directory:

```bash
python backup_cli.py
```

1. For credentials: create a file `.arcgis_credentials` (see below) or enter username and password when prompted.
2. Choose a folder from the numbered list.
3. Choose one or more layers/maps by number (e.g. `1` or `1,3,5`).
4. Enter an optional backup subpath, or leave blank to use `YYYYMONDD/Folder/type/name` (e.g. `backups/2026FEB11/My Maps/WebMap/BMFX_FuelBreaks_FieldWork`).
5. The export runs and prints the output path when done.

## Backup base path

By default, backups are saved under `./backups` (relative to the directory from which you run the app). To use another base directory:

```bash
export BACKUP_BASE_PATH=/path/to/your/backups
python backup_cli.py
```

The subpath you enter in step 4 is under this base (e.g. `2025-02`). Path traversal is blocked; you cannot escape the base directory.

## Optional: Credentials file

To avoid typing your username and password each run, create a file `.arcgis_credentials` in the project directory:

```
USERNAME=your_username
PASSWORD=your_password
```

**This file is listed in .gitignore and must never be committed.** To use a different path:

```bash
export AGO_CREDENTIALS_FILE=/path/to/your/credentials
python backup_cli.py
```

## Optional: ArcGIS Enterprise

By default the app connects to ArcGIS Online. For ArcGIS Enterprise:

```bash
export AGO_URL=https://gis.yourorg.com/portal
python backup_cli.py
```

## Project layout

- **backup_cli.py** – Main application (CLI).
- **app.py** – Shared library (constants and helpers for folders, items, paths); used by `backup_cli.py`.
- **requirements.txt** – Runtime dependencies (ArcGIS API only).
