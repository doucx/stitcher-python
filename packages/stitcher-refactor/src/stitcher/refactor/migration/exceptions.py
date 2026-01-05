class MigrationError(Exception):
    """Base exception for migration-related errors."""

    pass


class MigrationScriptError(MigrationError):
    """Raised when a migration script is invalid."""

    pass
