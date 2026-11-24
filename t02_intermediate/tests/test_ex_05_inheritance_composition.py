import pytest

from _loader import load

ex = load("t02_intermediate", "ex_05_inheritance_composition")


def test_employee_and_manager():
    emp = ex.Employee("Al", 500)
    assert emp.pay() == 500
    mgr = ex.Manager("Mo", 1000)
    assert issubclass(ex.Manager, ex.Employee)
    assert mgr.pay() == 1000
    mgr.add_report(emp)
    mgr.add_report(ex.Employee("Bo", 400))
    assert mgr.pay() == 2000
    assert mgr.name == "Mo"


def test_mro_names():
    class A: ...

    class B(A): ...

    class C(A): ...

    class D(B, C): ...

    assert ex.mro_names(A) == ["A"]
    assert ex.mro_names(D) == ["D", "B", "C", "A"]


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, to, message):
        self.sent.append((to, message))


def test_notifier_uses_injected_sender():
    sender = FakeSender()
    notifier = ex.Notifier(sender)
    assert notifier.notify_all(["a", "", "b"], "hi") == 2
    assert sender.sent == [("a", "hi"), ("b", "hi")]
    assert notifier.notify_all([], "hi") == 0


def test_stack_composition():
    s = ex.Stack()
    assert s.size() == 0
    s.push(1)
    s.push(2)
    assert s.peek() == 2
    assert s.pop() == 2
    assert s.size() == 1
    assert not isinstance(s, list)  # composition, not inheritance


def test_stack_empty_errors():
    s = ex.Stack()
    with pytest.raises(IndexError):
        s.pop()
    with pytest.raises(IndexError):
        s.peek()
