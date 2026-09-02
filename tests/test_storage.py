import tempfile
import unittest
from pathlib import Path

from clipboard_history.storage import ClipboardStore


class ClipboardStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = ClipboardStore(Path(self.directory.name) / "history.db", limit=3)

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_text_and_image_are_stored(self):
        self.assertTrue(self.store.add_text("hello"))
        self.assertTrue(self.store.add_image(b"png-data"))
        self.assertEqual([item.kind for item in self.store.items()], ["image", "text"])

    def test_limit_keeps_newest_items(self):
        for value in ("one", "two", "three", "four"):
            self.store.add_text(value)
        self.assertEqual(self.store.count(), 3)
        self.assertEqual([item.text for item in self.store.items()], ["four", "three", "two"])

    def test_duplicates_are_ignored(self):
        self.assertTrue(self.store.add_text("same"))
        self.assertFalse(self.store.add_text("same"))
        self.assertEqual(self.store.count(), 1)


if __name__ == "__main__":
    unittest.main()