"""
Tests for load_credentials_from_file.
"""
import tempfile
import unittest
from pathlib import Path

from app import load_credentials_from_file


class TestLoadCredentialsFromFile(unittest.TestCase):
    def test_valid_credentials_file(self) -> None:
        """Valid USERNAME=foo and PASSWORD=bar returns (username, password)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("USERNAME=foo\n")
            f.write("PASSWORD=bar\n")
            path = f.name
        try:
            result = load_credentials_from_file(path)
            self.assertIsNotNone(result)
            self.assertEqual(result, ("foo", "bar"))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_credentials_with_whitespace_around_equals(self) -> None:
        """Whitespace around = is allowed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("USERNAME = myuser\n")
            f.write("PASSWORD = mypass\n")
            path = f.name
        try:
            result = load_credentials_from_file(path)
            self.assertIsNotNone(result)
            self.assertEqual(result, ("myuser", "mypass"))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_credentials_with_comments_ignored(self) -> None:
        """Lines starting with # are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# comment\n")
            f.write("USERNAME=alice\n")
            f.write("# another comment\n")
            f.write("PASSWORD=secret\n")
            path = f.name
        try:
            result = load_credentials_from_file(path)
            self.assertIsNotNone(result)
            self.assertEqual(result, ("alice", "secret"))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_file_returns_none(self) -> None:
        """Non-existent file returns None."""
        result = load_credentials_from_file("/nonexistent/path/credentials.txt")
        self.assertIsNone(result)

    def test_empty_file_returns_none(self) -> None:
        """Empty file returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            result = load_credentials_from_file(path)
            self.assertIsNone(result)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_username_returns_none(self) -> None:
        """File with only PASSWORD returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("PASSWORD=bar\n")
            path = f.name
        try:
            result = load_credentials_from_file(path)
            self.assertIsNone(result)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_password_returns_none(self) -> None:
        """File with only USERNAME returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("USERNAME=foo\n")
            path = f.name
        try:
            result = load_credentials_from_file(path)
            self.assertIsNone(result)
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
