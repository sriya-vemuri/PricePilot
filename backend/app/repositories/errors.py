class RepositoryError(Exception):
    """Base persistence error. Wraps driver/ORM exceptions."""


class DatabaseError(RepositoryError):
    """Raised when a database operation fails."""
