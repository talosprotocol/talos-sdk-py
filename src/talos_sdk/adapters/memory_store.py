from talos_sdk.ports.audit_store import (
    AuditEvent,
    EventPage,
    Filters,
    IAuditStorePort,
    Stats,
    TimeWindow,
)
from talos_sdk.ports.key_value_store import IKeyValueStorePort


class InMemoryKeyValueStore(IKeyValueStorePort):
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self.store.get(key)

    def put(self, key: str, value: bytes) -> None:
        self.store[key] = value

    def delete(self, key: str) -> None:
        if key in self.store:
            del self.store[key]


class InMemoryAuditStore(IAuditStorePort):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self.events.append(event)

    def list(
        self,
        before: str | None = None,
        limit: int = 100,
        filters: Filters | None = None,
    ) -> EventPage:
        # Simplistic implementation: return last N events
        # Real implementation would use cursor logic
        sliced = self.events[-limit:] if self.events else []

        # We need to return an object matching EventPage Protocol
        class Page:
            def __init__(
                self, events: list[AuditEvent], next_cursor: str | None, has_more: bool
            ) -> None:
                self.events = events
                self.next_cursor = next_cursor
                self.has_more = has_more

        # For this simple implementation, has_more is always False
        return Page(sliced, None, False)

    def stats(self, window: TimeWindow) -> Stats:
        count = 0
        for e in self.events:
            if window.start <= e.timestamp <= window.end:
                count += 1

        class StatObj:
            def __init__(self, c: int) -> None:
                self.count = c

        return StatObj(count)
