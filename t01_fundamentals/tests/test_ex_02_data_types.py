from _loader import load

ex = load("t01_fundamentals", "ex_02_data_types")


def test_type_name():
    assert ex.type_name(5) == "int"
    assert ex.type_name([1]) == "list"
    assert ex.type_name(None) == "NoneType"
    assert ex.type_name(3.0) == "float"


def test_to_int_or_none():
    assert ex.to_int_or_none("42") == 42
    assert ex.to_int_or_none(" -7 ") == -7
    assert ex.to_int_or_none("4.2") is None
    assert ex.to_int_or_none("") is None


def test_is_collection():
    assert ex.is_collection([1, 2]) is True
    assert ex.is_collection({"a": 1}) is True
    assert ex.is_collection((1,)) is True
    assert ex.is_collection({1}) is True
    assert ex.is_collection(frozenset()) is True
    assert ex.is_collection("abc") is False
    assert ex.is_collection(5) is False


def test_bytes_to_text():
    assert ex.bytes_to_text(b"hi") == ("hi", 2)
    assert ex.bytes_to_text("é".encode()) == ("é", 2)
    assert ex.bytes_to_text(b"") == ("", 0)
