from typing import Type, TypeVar, Dict, Any, Callable

T = TypeVar("T")


class Container:
    """
    A simple thread-safe Dependency Injection container.
    """

    def __init__(self) -> None:
        self._services: Dict[Type[Any], Any] = {}
        self._factories: Dict[Type[Any], Callable[[], Any]] = {}

    def register(self, interface: Type[T], implementation: T) -> None:
        """Register a singleton instance for an interface."""
        self._services[interface] = implementation

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory for an interface (lazy or transient)."""
        self._factories[interface] = factory

    def resolve(self, interface: Type[T]) -> T:
        """Resolve an implementation for an interface."""
        if interface in self._services:
            return self._services[interface]

        if interface in self._factories:
            instance = self._factories[interface]()
            # Optionally cache if singleton desired, but keeping simple
            return instance

        raise ValueError(f"No registration found for {interface}")


# Global instance for easy access if needed
_global_container = Container()


def get_container() -> Container:
    return _global_container
