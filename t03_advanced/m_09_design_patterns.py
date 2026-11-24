# Design Patterns in Idiomatic Python
"""
The classic "Gang of Four" patterns were designed for languages without first-class
functions, duck typing or modules. In Python many of them shrink to a few lines:
- Strategy   -> pass a function (or a dict of functions).
- Factory    -> a registry dict, or a classmethod; classes are objects too.
- Adapter    -> a thin wrapper class that translates one interface to another.
- Observer   -> a list of callbacks (an event emitter).
- Repository -> a Protocol with get/add/list; swap in-memory for a database.
- Dependency injection -> pass collaborators in via __init__; no framework needed.
Rule of thumb: reach for a pattern to remove a concrete pain (hard to test, hard to
swap), not because it appears in a book. A module-level function is often enough.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

# Example: Strategy - behavior is just a callable passed in
type PriceRule = Callable[[float], float]


def no_discount(price: float) -> float:
    return price


def black_friday(price: float) -> float:
    return price * 0.7


def checkout(price: float, rule: PriceRule = no_discount) -> float:
    return round(rule(price), 2)


print("strategy:", checkout(100), checkout(100, black_friday), checkout(100, lambda p: p - 5))

# Example: Factory - a registry maps names to classes; register with a decorator
SERIALIZERS: dict[str, type] = {}


def register(name: str) -> Callable[[type], type]:
    def decorator(cls: type) -> type:
        SERIALIZERS[name] = cls
        return cls

    return decorator


@register("csv")
class CsvSerializer:
    def dumps(self, row: list[str]) -> str:
        return ",".join(row)


@register("tsv")
class TsvSerializer:
    def dumps(self, row: list[str]) -> str:
        return "\t".join(row)


def make_serializer(kind: str):
    try:
        return SERIALIZERS[kind]()
    except KeyError:
        raise ValueError(
            f"unknown serializer {kind!r}; choose from {sorted(SERIALIZERS)}"
        ) from None


print("factory:", repr(make_serializer("csv").dumps(["a", "b"])), sorted(SERIALIZERS))


# Example: Adapter - make a third-party style API fit the interface we expect
class LegacyTemperatureSensor:
    def read_fahrenheit(self) -> float:
        return 98.6


class CelsiusSensor(Protocol):
    def read_celsius(self) -> float: ...


class FahrenheitAdapter:
    def __init__(self, legacy: LegacyTemperatureSensor) -> None:
        self._legacy = legacy

    def read_celsius(self) -> float:
        return round((self._legacy.read_fahrenheit() - 32) * 5 / 9, 1)


def report(sensor: CelsiusSensor) -> str:
    return f"{sensor.read_celsius()} C"


print("adapter:", report(FahrenheitAdapter(LegacyTemperatureSensor())))


# Example: Observer - an event emitter is a dict of callback lists
class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[..., None]) -> Callable[[], None]:
        self._handlers[event].append(handler)
        return lambda: self._handlers[event].remove(handler)  # call to unsubscribe

    def publish(self, event: str, **payload: object) -> int:
        for handler in list(self._handlers[event]):  # copy: handlers may unsubscribe
            handler(**payload)
        return len(self._handlers[event])


bus = EventBus()
seen: list[str] = []
unsubscribe = bus.subscribe("user.created", lambda name: seen.append(f"welcome {name}"))
bus.publish("user.created", name="ada")
unsubscribe()
bus.publish("user.created", name="grace")  # nobody listening any more
print("observer:", seen)


# Example: Repository + dependency injection
@dataclass
class User:
    id: int
    name: str


class UserRepository(Protocol):
    def add(self, user: User) -> None: ...
    def get(self, user_id: int) -> User | None: ...


@dataclass
class InMemoryUserRepository:
    _rows: dict[int, User] = field(default_factory=dict)

    def add(self, user: User) -> None:
        self._rows[user.id] = user

    def get(self, user_id: int) -> User | None:
        return self._rows.get(user_id)


class UserService:
    # The repository is injected, so tests use a fake and production uses SQL.
    def __init__(self, repo: UserRepository, clock: Callable[[], str] = lambda: "now") -> None:
        self.repo = repo
        self.clock = clock

    def register(self, user_id: int, name: str) -> str:
        self.repo.add(User(user_id, name))
        return f"{name} registered at {self.clock()}"


service = UserService(InMemoryUserRepository(), clock=lambda: "12:00")
print("di:", service.register(1, "ada"), service.repo.get(1))

"""
Common mistakes
- Building a Strategy class hierarchy when a plain function would do.
- Hidden globals instead of injected dependencies: the code becomes untestable.
- A Singleton class; a module is already a singleton, so use a module-level instance.
- Observers that mutate the subscriber list while it is being iterated.
- Applying a pattern "just in case". Wait for the second concrete need.

Where this shows up in backend/ML/robotics work
- Strategy: swappable retry/backoff policies, loss functions, planners, tokenizers.
- Factory/registry: model or optimizer lookup by config string, plugin systems.
- Adapter: wrapping vendor SDKs (LLM providers, cloud storage) behind your interface.
- Observer: training callbacks, ROS-style topics, webhooks and domain events.
- Repository + DI: FastAPI `Depends`, database layers that tests replace with fakes.
"""
