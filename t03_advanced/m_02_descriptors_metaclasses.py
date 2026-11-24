# Descriptors and Metaclasses
"""
Descriptors and metaclasses are the machinery behind @property, @classmethod, dataclasses,
Django/SQLAlchemy models and Pydantic. You rarely write them, but you must read them.

DESCRIPTOR: an object stored on a CLASS that defines __get__, __set__ and/or __delete__.
Attribute access on an instance calls those methods.
- Data descriptor: defines __set__ (or __delete__); wins over the instance __dict__.
- Non-data descriptor: only __get__ (functions are these, which is how methods bind self).
- __set_name__(owner, name) is called at class creation so the descriptor learns its name.

METACLASS: the class of a class. `type` is the default. `class A(metaclass=Meta)` calls
Meta(name, bases, namespace) to build A.

Rule of thumb: need to customize a CLASS being created? Try, in order:
class decorator -> __init_subclass__ -> metaclass (last resort; metaclasses do not compose).
"""

from typing import Any


# Example: a reusable validated attribute (data descriptor + __set_name__)
class Positive:
    def __set_name__(self, owner: type, name: str) -> None:
        self.private = f"_{name}"  # where the value is stored on each instance
        self.public = name

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:  # accessed on the class itself: return the descriptor
            return self
        return getattr(obj, self.private)

    def __set__(self, obj: Any, value: float) -> None:
        if value <= 0:
            raise ValueError(f"{self.public} must be positive, got {value}")
        setattr(obj, self.private, value)


class Product:
    price = Positive()  # one descriptor instance shared by ALL products
    qty = Positive()

    def __init__(self, price: float, qty: int) -> None:
        self.price = price  # goes through Positive.__set__
        self.qty = qty


p = Product(9.5, 3)
print("price:", p.price, "| descriptor on class:", type(Product.price).__name__)
try:
    p.qty = -1
except ValueError as exc:
    print("rejected:", exc)


# Example: how @property works (it IS a descriptor) and how functions bind self
class Circle:
    def __init__(self, r: float) -> None:
        self.r = r

    @property
    def area(self) -> float:
        return 3.14159 * self.r**2


print("area:", Circle(2).area, "| property is a", type(Circle.__dict__["area"]).__name__)
bound = Circle.__init__.__get__(Circle(1), Circle)  # functions are non-data descriptors
print("method binding:", type(bound).__name__)


# Example: a non-data descriptor: lazy, computed once, then cached on the instance
class LazyAttr:
    def __init__(self, func: Any) -> None:
        self.func = func

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self
        value = self.func(obj)
        obj.__dict__[self.name] = value  # instance dict now shadows the non-data descriptor
        return value


class Report:
    @LazyAttr
    def total(self) -> int:
        print("  (computing total once)")
        return sum(range(1000))


r = Report()
print(r.total, r.total)  # computed once (functools.cached_property does exactly this)


# Example: type() builds classes; a class statement is sugar for it
Dog = type("Dog", (), {"sound": "woof", "speak": lambda self: self.sound})
print("type() made:", Dog().speak(), "| type(Dog) is", type(Dog).__name__)


# Example: a metaclass that auto-registers every subclass
class RegistryMeta(type):
    registry: dict[str, type] = {}

    def __new__(mcls, name: str, bases: tuple, ns: dict) -> type:
        cls = super().__new__(mcls, name, bases, ns)
        if bases:  # skip the base class itself
            mcls.registry[name.lower()] = cls
        return cls


class BaseHandler(metaclass=RegistryMeta):
    pass


class JsonHandler(BaseHandler):
    pass


class XmlHandler(BaseHandler):
    pass


print("metaclass registry:", sorted(RegistryMeta.registry))


# Example: the same job with __init_subclass__ (usually the better tool)
class Plugin:
    registry: dict[str, type[Plugin]] = {}

    def __init_subclass__(cls, /, key: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        Plugin.registry[key or cls.__name__.lower()] = cls


class Csv(Plugin):
    pass


class Parquet(Plugin, key="pq"):  # class keyword arguments are passed to the hook
    pass


print("__init_subclass__ registry:", sorted(Plugin.registry))


# Example: attribute lookup order (why data descriptors win)
class Probe:
    x = Positive()


probe = Probe()
probe.__dict__["x"] = "hidden"  # sneaking a value into the instance dict
probe.x = 5  # __set__ runs
print("data descriptor wins:", probe.x, "| instance dict value ignored:", probe.__dict__["x"])

"""
Common mistakes
- Storing the value ON the descriptor (self.value = ...). It is shared by every instance;
  store per-instance data in obj.__dict__ or a private attribute (use __set_name__).
- Forgetting `if obj is None: return self` in __get__, which breaks access via the class.
- Reaching for a metaclass when __init_subclass__ or a class decorator would do. Two
  libraries with different metaclasses cannot be combined (metaclass conflict).
- Using a descriptor without __set_name__ and hard-coding the attribute name.
- Keeping per-instance state in a dict on the descriptor keyed by obj: it leaks memory and
  breaks for unhashable objects. Prefer obj.__dict__.

Where this shows up in backend/ML/robotics work
- Backend: ORMs (SQLAlchemy Column, Django fields), Pydantic and dataclass field handling,
  cached_property, FastAPI-style dependency markers.
- ML: PyTorch nn.Module attribute registration, framework "registry" patterns for
  models, optimizers and datasets (usually __init_subclass__ today).
- Robotics: unit-checked or range-checked parameters (a Positive/Bounded descriptor),
  plugin registries for sensors and controllers.
"""
