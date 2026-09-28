import unittest

from revel.graph import Link, Node
from revel.store import MemoryGraphStore, open_store


class MemoryStoreTests(unittest.TestCase):
    def test_put_and_get_roundtrip(self) -> None:
        store = MemoryGraphStore()
        email = store.put_node(Node.create("email", "Re: contract"))
        task = store.put_node(Node.create("task", "Write brief"))
        link = store.put_link(Link.create(email, task, "assigned"))
        self.assertEqual(store.get_node(task.id).title, "Write brief")
        self.assertEqual(store.links_from(email.id)[0].id, link.id)
        self.assertEqual(store.links_to(task.id)[0].kind, "assigned")
        store.close()

    def test_link_requires_both_nodes(self) -> None:
        store = MemoryGraphStore()
        task = store.put_node(Node.create("task", "Write brief"))
        orphan = Node.create("email", "Missing")
        with self.assertRaises(KeyError):
            store.put_link(Link.create(orphan, task, "assigned"))

    def test_factory_memory(self) -> None:
        store = open_store(engine="memory")
        node = store.put_node(Node.create("file", "brief.md"))
        self.assertIsNotNone(store.get_node(node.id))


if __name__ == "__main__":
    unittest.main()
