import pytest

from _loader import load

ex = load("t01_fundamentals", "ex_08_loops")


def test_sum_of_evens():
    assert ex.sum_of_evens(10) == 30
    assert ex.sum_of_evens(11) == 30
    assert ex.sum_of_evens(1) == 0
    assert ex.sum_of_evens(0) == 0


def test_fizzbuzz_list():
    assert ex.fizzbuzz_list(5) == ["1", "2", "Fizz", "4", "Buzz"]
    assert ex.fizzbuzz_list(0) == []
    assert ex.fizzbuzz_list(15)[-1] == "FizzBuzz"


def test_first_repeated():
    assert ex.first_repeated([1, 2, 3, 2, 1]) == 2
    assert ex.first_repeated(["a", "b"]) is None
    assert ex.first_repeated([]) is None
    assert ex.first_repeated([5, 5]) == 5


def test_number_lines():
    assert ex.number_lines(["a", "b"]) == ["1: a", "2: b"]
    assert ex.number_lines([]) == []


def test_collatz_steps():
    assert ex.collatz_steps(1) == 0
    assert ex.collatz_steps(6) == 8
    assert ex.collatz_steps(27) == 111
    with pytest.raises(ValueError):
        ex.collatz_steps(0)
