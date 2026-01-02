from abc import ABC, abstractmethod
from typing import Protocol, List, Optional

# Placeholder for models - in a real scenario these would come from talos-contracts
# But since talos-contracts might not be in the python path of this agent environment,
# I will define Protocol or use Any for now, or assume imports work.
# The user's prompt showed `event: AuditEvent`.
# I will try to import from talos_contracts if possible, or define type aliases.


class AuditEvent(Protocol):
    event_id: str
    timestamp: float
    # ...


class Filters(Protocol):
    pass


class EventPage(Protocol):
    events: List[AuditEvent]
    next_cursor: Optional[str]


class Stats(Protocol):
    count: int


class TimeWindow(Protocol):
    start: float
    end: float


class IAuditStorePort(ABC):
    """
    Port for storing and retrieving audit events.
    Cohesive grouping of audit log storage operations.
    """

    @abstractmethod
    def append(self, event: AuditEvent) -> None:
        """Append a new audit event to the immutable log."""
        ...

    @abstractmethod
    def list(
        self, before: Optional[str] = None, limit: int = 100, filters: Optional[Filters] = None
    ) -> EventPage:
        """List events with pagination (cursor-based) and filtering."""
        ...

    @abstractmethod
    def stats(self, window: TimeWindow) -> Stats:
        """Retrieve statistics for a time window."""
        ...
