import os
import tempfile
import unittest
from pathlib import Path

from revel.adapters.fs import files_root, ingest_file, revel_home
from revel.plane import create_node
from revel.store import MemoryGraphStore


class FilesystemAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["REVEL_HOME"] = str(Path(self.tmp.name) / "Revel")
        os.environ["HOME"] = self.tmp.name

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_home_is_capital_revel(self) -> None:
        self.assertTrue(str(revel_home()).endswith("Revel"))
        self.assertEqual(files_root(), revel_home() / "files")

    def test_ingest_copies_once_by_hash(self) -> None:
        store = MemoryGraphStore()
        src = Path(self.tmp.name) / "brief.md"
        src.write_text("hello revel\n")
        first = ingest_file(store, src)
        second = ingest_file(store, src)
        self.assertEqual(first.id, second.id)
        dest = Path(first.payload["path"])
        self.assertTrue(dest.is_file())
        self.assertEqual(dest.parent, files_root())
        self.assertEqual(dest.read_text(), "hello revel\n")

    def test_attach_link(self) -> None:
        store = MemoryGraphStore()
        task = create_node(store, "task", "Write brief")
        src = Path(self.tmp.name) / "note.txt"
        src.write_text("x")
        node = ingest_file(store, src, attach_to=task.id)
        links = store.links_from(node.id)
        self.assertEqual(links[0].kind, "attached")
        self.assertEqual(links[0].target_id, task.id)


if __name__ == "__main__":
    unittest.main()
