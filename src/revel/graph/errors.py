class UnknownNodeTypeError(ValueError):
    """Request used a type the registry does not know."""


class UnknownLinkKindError(ValueError):
    """Request used a link kind the registry does not know."""
