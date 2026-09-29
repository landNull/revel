import unittest

from revel.plane import create_node
from revel.projection.kanban import board, column_of, move_card, to_jkanban
from revel.store import MemoryGraphStore


class KanbanProjectionTests(unittest.TestCase):
    def test_default_column_and_move(self) -> None:
        store = MemoryGraphStore()
        task = create_node(store, "task", "Write brief")
        email = create_node(store, "email", "Re: contract")
        self.assertEqual(column_of(task), "todo")
        move_card(store, task.id, "doing")
        columns = board(store)
        self.assertEqual([n.title for n in columns["doing"]], ["Write brief"])
        self.assertEqual([n.title for n in columns["todo"]], ["Re: contract"])
        payload = to_jkanban(store)
        self.assertEqual([col["id"] for col in payload], ["todo", "doing", "done"])

    def test_reject_unknown_column(self) -> None:
        store = MemoryGraphStore()
        task = create_node(store, "task", "Write brief")
        with self.assertRaises(ValueError):
            move_card(store, task.id, "blocked")


if __name__ == "__main__":
    unittest.main()
