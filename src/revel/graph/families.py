"""Named subsets of the same registry. Not separate apps (#10–#14)."""

WORK_TYPES = frozenset({"task", "project", "milestone"})
CRM_TYPES = frozenset({"lead", "opportunity", "account", "contact"})
COMMS_TYPES = frozenset({"file", "email", "event"})
SUPPORT_TYPES = frozenset({"ticket"})
MARKETING_TYPES = frozenset({"campaign", "content", "inventory_item", "knowledge_article"})
IDENTITY_TYPES = frozenset({"user", "group"})
