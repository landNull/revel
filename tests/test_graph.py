import unittest

from revel.graph import (
    CORE_NODE_TYPES,
    COMMS_TYPES,
    CRM_TYPES,
    IDENTITY_TYPES,
    Link,
    MARKETING_TYPES,
    Node,
    SUPPORT_TYPES,
    UnknownNodeTypeError,
    WORK_TYPES,
    default_registry,
)


class GraphTests(unittest.TestCase):
    def test_seventeen_core_types(self) -> None:
        self.assertEqual(len(CORE_NODE_TYPES), 17)
        self.assertEqual(set(default_registry.names()), set(CORE_NODE_TYPES))

    def test_families_cover_core_without_overlap_gap(self) -> None:
        union = (
            WORK_TYPES
            | CRM_TYPES
            | COMMS_TYPES
            | SUPPORT_TYPES
            | MARKETING_TYPES
            | IDENTITY_TYPES
        )
        self.assertEqual(union, set(CORE_NODE_TYPES))

    def test_create_any_type_and_cross_link(self) -> None:
        email = Node.create("email", "Re: contract")
        task = Node.create("task", "Write brief")
        link = Link.create(email, task, "assigned")
        self.assertEqual(link.source_id, email.id)
        self.assertEqual(link.target_id, task.id)
        self.assertEqual(link.kind, "assigned")

    def test_unknown_type_rejected(self) -> None:
        with self.assertRaises(UnknownNodeTypeError):
            Node.create("spaceship", "Nope")

    def test_registry_is_extensible(self) -> None:
        from revel.graph import NodeTypeRegistry

        extra = NodeTypeRegistry()
        extra.register("note")
        note = Node.create("note", "Parking lot", registry=extra)
        self.assertEqual(note.type, "note")

    def test_identity_is_not_os_account(self) -> None:
        user = Node.create("user", "landnull")
        group = Node.create("group", "core")
        link = Link.create(user, group, "member_of")
        self.assertEqual(user.type, "user")
        self.assertEqual(link.kind, "member_of")


if __name__ == "__main__":
    unittest.main()
