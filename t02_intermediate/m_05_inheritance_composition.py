# Inheritance and Composition
"""
Inheritance: a subclass reuses and specializes a parent ("is-a").
    class Dog(Animal): ...
super() calls the next class in the Method Resolution Order (MRO).
Multiple inheritance is allowed; Python computes a linear MRO (C3 linearization).
Composition: an object HOLDS other objects and delegates to them ("has-a").
Guideline: prefer composition over inheritance. Inherit only for a true "is-a"
relationship or to implement a shared interface; compose to combine behaviour.
"""


# Example: basic inheritance with super()
class Animal:
    def __init__(self, name: str) -> None:
        self.name = name

    def speak(self) -> str:
        return "..."

    def describe(self) -> str:
        return f"{self.name} says {self.speak()}"


class Dog(Animal):
    def __init__(self, name: str, breed: str) -> None:
        super().__init__(name)  # initialise the parent part
        self.breed = breed

    def speak(self) -> str:  # override
        return "Woof"


class Cat(Animal):
    def speak(self) -> str:
        return "Meow"


for pet in (Dog("Rex", "lab"), Cat("Tom"), Animal("Thing")):
    print(pet.describe())  # polymorphism: same call, different behaviour

print(isinstance(Dog("a", "b"), Animal), issubclass(Cat, Animal))


# Example: multiple inheritance and the MRO (the diamond problem)
class A:
    def hello(self) -> str:
        return "A"


class B(A):
    def hello(self) -> str:
        return "B>" + super().hello()


class C(A):
    def hello(self) -> str:
        return "C>" + super().hello()


class D(B, C):
    def hello(self) -> str:
        return "D>" + super().hello()


print([cls.__name__ for cls in D.__mro__])
print(D().hello())  # each class appears exactly once: D>B>C>A


# Example: mixin, a small class that adds one capability
class JsonMixin:
    def to_json(self) -> str:
        import json

        return json.dumps(vars(self))


class User(JsonMixin):
    def __init__(self, name: str) -> None:
        self.name = name


print(User("ada").to_json())


# Example: composition. A Car HAS an Engine instead of IS-A Engine
class Engine:
    def __init__(self, horsepower: int) -> None:
        self.horsepower = horsepower

    def start(self) -> str:
        return f"engine({self.horsepower}hp) running"


class Car:
    def __init__(self, engine: Engine) -> None:  # engine is injected
        self.engine = engine

    def drive(self) -> str:
        return f"car: {self.engine.start()}"


print(Car(Engine(150)).drive())


# Composition lets you swap collaborators easily (great for testing)
class FakeEngine(Engine):
    def start(self) -> str:
        return "fake engine"


print(Car(FakeEngine(0)).drive())

"""
Common mistakes
- Forgetting super().__init__(...) so parent attributes are never set.
- Inheriting just to reuse code when the relationship is not "is-a"
  (a Stack is NOT a list; hold a list inside instead).
- Deep hierarchies that are hard to follow. Keep them shallow.
- Hard-coding parent names (Parent.method(self)) instead of super(), breaking the MRO.
- Overriding a method with an incompatible signature (breaks substitutability).
"""

"""
Where this shows up in backend/ML work
- Framework base classes: custom exceptions, Django views, torch.nn.Module subclasses.
- Dependency injection in FastAPI/services is composition: pass in a repository or client.
- Mixins add logging, timestamps, or serialization to many models.
- Swapping a real LLM client for a fake in tests works because of composition.
"""
