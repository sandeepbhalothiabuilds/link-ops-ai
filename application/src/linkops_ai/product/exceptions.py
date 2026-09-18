class LinkOpsError(Exception):
    """Base class for expected application errors."""


class InvalidDestinationUrl(LinkOpsError):
    pass


class InvalidAlias(LinkOpsError):
    pass


class AliasAlreadyExists(LinkOpsError):
    pass


class AliasGenerationExhausted(LinkOpsError):
    pass


class LinkNotFound(LinkOpsError):
    pass


class LinkExpired(LinkOpsError):
    pass


class LinkInactive(LinkOpsError):
    pass


class PersistenceUnavailable(LinkOpsError):
    pass


class AnalyticsUnavailable(LinkOpsError):
    pass
