"""
Tests that verify Search results correctly populate the Item IDs list for backup.

- Backend: after search, the index page renders search results with data-id attributes
  and the backup form has item_ids textarea; session search_results are passed correctly.
- Add-selected logic: the same merge/dedupe behavior used by the front-end is verified
  (simulated in Python). Optional: Playwright e2e test runs the real JS in a browser.
"""
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import app after we may have changed env so session dir exists
from app import app, get_gis


# Fake ArcGIS items for mocked search
def _make_mock_item(item_id: str, title: str = "", item_type: str = "Feature Service"):
    o = type("Item", (), {})()
    o.id = item_id
    o.title = title or f"Item {item_id}"
    o.type = item_type
    return o


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def mock_gis():
    """Mock GIS that returns fake search results."""
    mock = type("GIS", (), {})()
    mock.content = type("Content", (), {})()
    mock.content.search = lambda query, item_type, max_items=100: [
        _make_mock_item("abc111", "My Feature Service", "Feature Service"),
        _make_mock_item("def222", "My Web Map", "Web Map"),
    ]
    mock.users = type("Users", (), {})()
    mock.users.me = type("Me", (), {"folders": []})()
    return mock


def test_search_results_rendered_with_data_ids(client, mock_gis):
    """After login and search, index page contains checkboxes with data-id and Add selected button."""
    with patch("app.get_gis", return_value=mock_gis):
        # Login (session will have logged_in, gis_url, username, password)
        client.post(
            "/login",
            data={
                "gis_url": "https://www.arcgis.com",
                "username": "testuser",
                "password": "testpass",
            },
            follow_redirects=True,
        )
        # Search
        r = client.post(
            "/search",
            data={"item_type": "Feature Service", "content_folder": ""},
            follow_redirects=True,
        )
    assert r.status_code == 200
    html = r.data.decode("utf-8")

    # Search results section must contain checkboxes with data-id for our mock items
    assert 'class="search-item-cb"' in html
    assert 'data-id="abc111"' in html
    assert 'data-id="def222"' in html
    # Add selected button and item_ids textarea must be present
    assert 'id="add-selected"' in html
    assert 'id="item_ids"' in html
    assert 'name="item_ids"' in html


def test_search_results_structure_matches_expected_for_add_selected(client, mock_gis):
    """Rendered search results have the exact structure the Add-selected script expects."""
    with patch("app.get_gis", return_value=mock_gis):
        client.post(
            "/login",
            data={"gis_url": "https://www.arcgis.com", "username": "u", "password": "p"},
            follow_redirects=True,
        )
        r = client.post(
            "/search",
            data={"item_type": "Feature Service", "content_folder": ""},
            follow_redirects=True,
        )
    assert r.status_code == 200
    html = r.data.decode("utf-8")

    # Extract all data-id values from .search-item-cb (same selector as the script)
    pattern = re.compile(
        r'<input[^>]*class="[^"]*search-item-cb[^"]*"[^>]*data-id="([^"]*)"',
        re.IGNORECASE,
    )
    data_ids = pattern.findall(html)
    assert data_ids == ["abc111", "def222"]


def test_add_selected_logic_merge_and_dedupe():
    """
    Verify the same logic as the front-end: merge selected IDs with existing,
    dedupe, join with newline. This mirrors the JS in index.html.
    """
    def add_selected_logic(existing_text: str, selected_ids: list[str]) -> str:
        existing = (existing_text or "").strip()
        existing_ids = re.split(r"[\s,\n]+", existing) if existing else []
        existing_ids = [x for x in existing_ids if x]
        combined = existing_ids + selected_ids
        seen = set()
        unique = []
        for id_ in combined:
            if id_ not in seen:
                seen.add(id_)
                unique.append(id_)
        return "\n".join(unique)

    # Empty textarea + two selected -> two IDs
    assert add_selected_logic("", ["abc111", "def222"]) == "abc111\ndef222"
    # Existing ID + one selected -> merged, deduped
    assert add_selected_logic("abc111", ["def222"]) == "abc111\ndef222"
    # Duplicate selected not added twice
    assert add_selected_logic("", ["abc111", "abc111"]) == "abc111"
    # Existing comma-separated parsed correctly
    assert add_selected_logic("id1, id2", ["id3"]) == "id1\nid2\nid3"


def test_backup_form_receives_item_ids_from_textarea(client, mock_gis):
    """Backup endpoint receives item_ids from the form; normalize_item_ids parses them."""
    from app import normalize_item_ids

    assert normalize_item_ids("abc111\ndef222") == ["abc111", "def222"]
    assert normalize_item_ids("abc111, def222") == ["abc111", "def222"]
    assert normalize_item_ids("  abc111  \n  def222  ") == ["abc111", "def222"]

    # Simulate form submit with item_ids populated (e.g. from Add selected)
    with patch("app.get_gis", return_value=mock_gis):
        with patch("app.resolve_items_by_ids") as resolve:
            with patch("app.safe_backup_path", return_value=Path(tempfile.gettempdir())):
                resolve.return_value = (
                    [_make_mock_item("abc111"), _make_mock_item("def222")],
                    [],
                )
                with patch.object(mock_gis.content, "offline") as offline:
                    offline.export_items = lambda items, path: type("Result", (), {"path": path})()

                    client.post(
                        "/login",
                        data={
                            "gis_url": "https://www.arcgis.com",
                            "username": "u",
                            "password": "p",
                        },
                        follow_redirects=True,
                    )
                    r = client.post(
                        "/backup",
                        data={
                            "item_ids": "abc111\ndef222",
                            "backup_path": "",
                        },
                        follow_redirects=True,
                    )
    assert r.status_code == 200
    resolve.assert_called_once()
    call_args = resolve.call_args[0]
    assert call_args[1] == ["abc111", "def222"]


def _playwright_available():
    import importlib.util
    return importlib.util.find_spec("playwright") is not None


@pytest.mark.skipif(
    not _playwright_available(),
    reason="Playwright not installed; pip install playwright && playwright install chromium",
)
def test_add_selected_populates_item_ids_in_browser(client, mock_gis):
    """
    E2E: Render index with search results, then in a real browser click Add selected
    and assert the item_ids textarea contains the selected IDs.
    """
    from playwright.sync_api import sync_playwright

    with patch("app.get_gis", return_value=mock_gis):
        client.post(
            "/login",
            data={"gis_url": "https://www.arcgis.com", "username": "u", "password": "p"},
            follow_redirects=True,
        )
        client.post(
            "/search",
            data={"item_type": "Feature Service", "content_folder": ""},
            follow_redirects=True,
        )
        r = client.get("/")
    assert r.status_code == 200
    html = r.data.decode("utf-8")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        path = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"file://{path}")
            # Check first two checkboxes (our two mock items)
            page.locator(".search-item-cb").nth(0).check()
            page.locator(".search-item-cb").nth(1).check()
            page.locator("#add-selected").click()
            value = page.locator("#item_ids").input_value()
            browser.close()
        assert value.strip() == "abc111\ndef222"
    finally:
        Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
