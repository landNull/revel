import unittest

from revel.demo import dashboard, load_demo
from revel.projection.kanban import board
from revel.store import MemoryGraphStore


class DemoTests(unittest.TestCase):
    def test_load_is_idempotent_and_covers_types(self) -> None:
        store = MemoryGraphStore()
        first = load_demo(store)
        second = load_demo(store)
        self.assertEqual(first["nodes"], second["nodes"])
        self.assertEqual(first["total_nodes"], second["total_nodes"])
        snap = dashboard(store)
        self.assertTrue(snap["demo_loaded"])
        self.assertGreaterEqual(len(snap["by_type"]), 17)
        cols = board(store)
        self.assertTrue(cols["todo"])
        self.assertTrue(cols["doing"])
        self.assertTrue(cols["done"])


if __name__ == "__main__":
    unittest.main()
