# Enums
"""
An Enum is a fixed set of named constants. It replaces "magic strings" and numbers
with something that is checked, self-documenting and iterable.
    Enum     -> plain members; compare by identity
    IntEnum  -> members are also ints (works with comparisons and int APIs)
    StrEnum  -> members are also strs (great for JSON and HTTP values), Python 3.11+
    Flag     -> members combinable with | and &
    auto()   -> let Python pick the values
match/case works well with enums for branching on a state.
"""

from enum import Enum, IntEnum, StrEnum, auto


# Example: basic Enum
class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


print(Color.RED, Color.RED.name, Color.RED.value)
print(Color(2), Color["BLUE"])  # lookup by value and by name
print(list(Color))
print(Color.RED is Color.RED, Color.RED == Color.GREEN)

try:
    Color(99)
except ValueError as exc:
    print("bad value:", exc)


# Example: auto() picks values for you
class Status(Enum):
    PENDING = auto()
    RUNNING = auto()
    DONE = auto()


print([(s.name, s.value) for s in Status])


# Example: IntEnum behaves like an int
class Priority(IntEnum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10


print(Priority.HIGH > Priority.LOW, Priority.MEDIUM + 1, sorted([Priority.HIGH, Priority.LOW]))


# Example: StrEnum behaves like a str
class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    GUEST = auto()  # auto() in StrEnum gives the lowercase member name: "guest"


print(Role.ADMIN == "admin", f"role={Role.USER}", Role.GUEST.value)
print(Role("admin"), [r.value for r in Role])


# Example: members can carry behaviour
class Planet(Enum):
    MERCURY = (3.303e23, 2.4397e6)
    EARTH = (5.976e24, 6.37814e6)

    def __init__(self, mass: float, radius: float) -> None:
        self.mass = mass
        self.radius = radius

    @property
    def gravity(self) -> float:
        return 6.67300e-11 * self.mass / (self.radius * self.radius)


print(f"{Planet.EARTH.gravity:.2f}")


# Example: match statement with enum members (note the dotted names)
def describe(status: Status) -> str:
    match status:
        case Status.PENDING:
            return "waiting"
        case Status.RUNNING:
            return "in progress"
        case Status.DONE:
            return "finished"


print([describe(s) for s in Status])


# Example: aliases and uniqueness
class Shape(Enum):
    SQUARE = 1
    BOX = 1  # alias: same value, same member


print(Shape.BOX is Shape.SQUARE, list(Shape))

"""
Common mistakes
- Comparing an Enum member to its raw value: Color.RED == 1 is False for a plain Enum.
  Use IntEnum/StrEnum, or compare .value deliberately.
- In match, writing `case RED:` (a capture pattern that matches anything).
  Use the dotted name `case Color.RED:`.
- Reusing a value, which silently creates an alias.
- Using strings everywhere instead of an enum, so typos like "runing" slip through.
- Mutating enum members; they are constants.
"""

"""
Where this shows up in backend/ML work
- API fields: FastAPI/Pydantic validate a StrEnum query param and document allowed values.
- Job/task states in queues and DB columns (PENDING, RUNNING, FAILED).
- HTTP methods, log levels (logging uses int levels), model/task type selectors.
- Config options like Device.CPU / Device.CUDA for ML runtimes.
"""
