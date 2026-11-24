# Dataclasses
"""
@dataclass generates __init__, __repr__ and __eq__ from annotated fields,
so you write the data and Python writes the boilerplate.
Options:
    field(default_factory=list)  -> safe mutable default
    frozen=True                  -> immutable + hashable
    slots=True                   -> less memory, no accidental new attributes
    order=True                   -> generates <, <=, >, >= comparing fields in order
    __post_init__                -> validation / derived fields after __init__
    kw_only=True                 -> all fields keyword-only
"""

from dataclasses import asdict, dataclass, field, replace


# Example: the basics
@dataclass
class Point:
    x: float
    y: float = 0.0  # fields with defaults must come after those without


p = Point(1.5)
print(p, p == Point(1.5, 0.0))


# Example: mutable defaults need default_factory
@dataclass
class Playlist:
    name: str
    songs: list[str] = field(default_factory=list)
    plays: int = field(default=0, repr=False)  # hidden from repr


a, b = Playlist("a"), Playlist("b")
a.songs.append("song")
print(a, b)  # b is unaffected


# Example: __post_init__ for validation and derived fields
@dataclass
class Rectangle:
    width: float
    height: float
    area: float = field(init=False)  # computed, not an __init__ argument

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("sides must be positive")
        self.area = self.width * self.height


print(Rectangle(3, 4))
try:
    Rectangle(-1, 2)
except ValueError as exc:
    print("invalid:", exc)


# Example: frozen makes instances immutable and hashable
@dataclass(frozen=True)
class Coord:
    lat: float
    lon: float


c = Coord(1.0, 2.0)
try:
    c.lat = 5.0  # type: ignore[misc]
except Exception as exc:
    print(type(exc).__name__)
print({c: "home"}[Coord(1.0, 2.0)])  # usable as a dict key
print(replace(c, lat=9.0))  # "modify" by making a copy


# Example: order=True and sorting
@dataclass(order=True)
class Version:
    major: int
    minor: int = 0


print(sorted([Version(1, 5), Version(1, 2), Version(0, 9)]))
print(Version(2) > Version(1, 9))


# Example: sort by one field only, using field(compare=False)
@dataclass(order=True)
class Task:
    priority: int
    title: str = field(compare=False)


print(min(Task(3, "low"), Task(1, "urgent")).title)


# Example: slots=True and kw_only=True
@dataclass(slots=True, kw_only=True)
class Job:
    name: str
    retries: int = 3


job = Job(name="etl")
print(job, hasattr(job, "__dict__"))
try:
    job.nme = "typo"  # type: ignore[attr-defined]
except AttributeError:
    print("slots stop typos")

# Example: converting to a dict (handy for JSON)
print(asdict(Playlist("mix", ["x", "y"])))

"""
Common mistakes
- Mutable defaults like songs: list = [] raise ValueError; use field(default_factory=list).
- Non-default field after a default field (TypeError); reorder or use kw_only=True.
- Expecting type annotations to be enforced at runtime. They are not; validate yourself
  (or use Pydantic).
- frozen=True only protects the attribute binding, not a list inside the object.
- Using order=True without thinking about which field order defines the comparison.
"""

"""
Where this shows up in backend/ML work
- Domain objects, DTOs, config objects and experiment records.
- Pydantic models and SQLModel follow the same annotated-class idea (with validation).
- Frozen dataclasses make safe cache keys and immutable settings.
- asdict() feeds json.dumps when logging structured events or saving run metadata.
"""
