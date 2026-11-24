from _loader import load

ex = load("t01_fundamentals", "ex_17_file_io")


def test_write_lines(tmp_path):
    p = tmp_path / "a.txt"
    ex.write_lines(p, ["a", "b"])
    assert p.read_text(encoding="utf-8") == "a\nb\n"
    ex.write_lines(p, [])
    assert p.read_text(encoding="utf-8") == ""


def test_read_lines(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("a\nb\n", encoding="utf-8")
    assert ex.read_lines(p) == ["a", "b"]
    assert ex.read_lines(tmp_path / "missing.txt") == []
    p.write_text("", encoding="utf-8")
    assert ex.read_lines(p) == []


def test_append_line(tmp_path):
    p = tmp_path / "log.txt"
    ex.append_line(p, "x")
    ex.append_line(p, "y")
    assert p.read_text(encoding="utf-8") == "x\ny\n"


def test_count_words(tmp_path):
    p = tmp_path / "w.txt"
    p.write_text("hello world\nfoo\n\n  bar   baz ", encoding="utf-8")
    assert ex.count_words(p) == 5
    p.write_text("", encoding="utf-8")
    assert ex.count_words(p) == 0


def test_json_roundtrip(tmp_path):
    p = tmp_path / "d.json"
    data = {"a": [1, 2], "b": {"c": None, "d": True}, "name": "café"}
    ex.save_json(p, data)
    assert ex.load_json(p) == data
    ex.save_json(p, {})
    assert ex.load_json(p) == {}
