from abc import ABC, abstractmethod

from talos_sdk.container import Container


class IService(ABC):
    @abstractmethod
    def do(self): ...


class ServiceImpl(IService):
    def do(self):
        return "done"


def test_container_singleton():
    c = Container()
    impl = ServiceImpl()
    c.register(IService, impl)

    assert c.resolve(IService) is impl
    assert c.resolve(IService).do() == "done"


def test_container_factory():
    c = Container()
    c.register_factory(IService, lambda: ServiceImpl())

    s1 = c.resolve(IService)
    s2 = c.resolve(IService)
    assert s1 is not s2
    assert s1.do() == "done"


def test_resolve_missing():
    c = Container()
    try:
        c.resolve(IService)
        assert False
    except ValueError:
        assert True
