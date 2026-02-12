"""
Tests for default_backup_subpath.
"""
import unittest
from datetime import datetime

from app import default_backup_subpath


class TestDefaultBackupSubpath(unittest.TestCase):
    def test_single_item_with_type(self) -> None:
        """Subpath uses YYYYMONDD/Folder/type/name format."""
        result = default_backup_subpath(
            "My Maps", [("My Map", "Web Map")], now=datetime(2026, 2, 11)
        )
        self.assertEqual(result, "2026FEB11/My Maps/WebMap/My Map")

    def test_feature_service_type(self) -> None:
        """Feature Service type becomes FeatureService (no space)."""
        result = default_backup_subpath(
            "Data", [("Parcels", "Feature Service")], now=datetime(2026, 2, 11)
        )
        self.assertEqual(result, "2026FEB11/Data/FeatureService/Parcels")

    def test_user_example_format(self) -> None:
        """Example: WebMap/BMFX_FuelBreaks_FieldWork."""
        result = default_backup_subpath(
            "Folder", [("BMFX_FuelBreaks_FieldWork", "Web Map")], now=datetime(2026, 2, 11)
        )
        self.assertEqual(result, "2026FEB11/Folder/WebMap/BMFX_FuelBreaks_FieldWork")

    def test_date_format_uppercase_month(self) -> None:
        """Month is 3-letter uppercase (e.g. FEB)."""
        result = default_backup_subpath(
            "Folder", [("Item", "Web Map")], now=datetime(2025, 12, 3)
        )
        self.assertEqual(result, "2025DEC03/Folder/WebMap/Item")

    def test_multiple_items_joined_with_underscore(self) -> None:
        """Multiple items are joined with underscore, each is type/name."""
        result = default_backup_subpath(
            "Data",
            [
                ("Layer1", "Feature Service"),
                ("Layer2", "Feature Service"),
                ("Map1", "Web Map"),
            ],
            now=datetime(2026, 1, 15),
        )
        self.assertEqual(
            result, "2026JAN15/Data/FeatureService/Layer1_FeatureService/Layer2_WebMap/Map1"
        )

    def test_sanitizes_invalid_path_characters(self) -> None:
        """Invalid path chars (/ \\ : * ? " < > |) are replaced with underscore."""
        result = default_backup_subpath(
            "My/Folder:Name",
            [("Layer with?invalid*chars", "Feature Service")],
            now=datetime(2026, 2, 11),
        )
        self.assertEqual(
            result, "2026FEB11/My_Folder_Name/FeatureService/Layer with_invalid_chars"
        )

    def test_empty_folder_title_becomes_unnamed(self) -> None:
        """Empty folder title becomes 'unnamed'."""
        result = default_backup_subpath(
            "", [("My Map", "Web Map")], now=datetime(2026, 2, 11)
        )
        self.assertEqual(result, "2026FEB11/unnamed/WebMap/My Map")

    def test_empty_item_list_becomes_unnamed(self) -> None:
        """Empty item list yields 'unnamed' for item part."""
        result = default_backup_subpath("Folder", [], now=datetime(2026, 2, 11))
        self.assertEqual(result, "2026FEB11/Folder/unnamed")

    def test_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace is stripped before sanitize."""
        result = default_backup_subpath(
            "  Folder  ", [("  Item  ", "Web Map")], now=datetime(2026, 2, 11)
        )
        self.assertEqual(result, "2026FEB11/Folder/WebMap/Item")


if __name__ == "__main__":
    unittest.main()
