import unittest


class WebAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            from fastapi.testclient import TestClient
            from revel.store import MemoryGraphStore
            from revel.web import create_app, set_store
        except ImportError:
            self.skipTest("fastapi not installed")
        set_store(MemoryGraphStore())
        self.client = TestClient(create_app())

    def test_create_and_board(self) -> None:
        created = self.client.post(
            "/nodes", json={"type": "task", "title": "Write brief"}
        )
        self.assertEqual(created.status_code, 200)
        node_id = created.json()["id"]
        listed = self.client.get("/nodes")
        self.assertEqual(listed.json()[0]["title"], "Write brief")
        board = self.client.get("/board").json()
        todo_ids = [item["id"] for col in board if col["id"] == "todo" for item in col["item"]]
        self.assertIn(node_id, todo_ids)
        page = self.client.get("/ui/board")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Sortable", page.text)
        self.assertIn("bootstrap", page.text)
        self.assertIn("/static/ui/revel.css", page.text)
        css = self.client.get("/static/ui/revel.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn("--revel-accent", css.text)
        cal = self.client.get("/ui/calendar")
        self.assertEqual(cal.status_code, 200)
        self.assertIn("themeSystem", cal.text)
        self.assertIn("bootstrap5", cal.text)


if __name__ == "__main__":
    unittest.main()
