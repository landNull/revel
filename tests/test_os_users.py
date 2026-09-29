import os
import unittest

from revel.adapters.os_users import current_uid, sync_current, user_node_id
from revel.store import MemoryGraphStore


class OsUsersTests(unittest.TestCase):
    def test_sync_current_is_idempotent(self) -> None:
        store = MemoryGraphStore()
        first, group = sync_current(store)
        second, _ = sync_current(store)
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.id, user_node_id(current_uid()))
        self.assertEqual(first.type, "user")
        self.assertEqual(first.payload["uid"], os.getuid())
        self.assertTrue(str(first.payload["revel_home"]).endswith("Revel"))
        if group is not None:
            kinds = [link.kind for link in store.links_from(first.id)]
            self.assertIn("member_of", kinds)


if __name__ == "__main__":
    unittest.main()
