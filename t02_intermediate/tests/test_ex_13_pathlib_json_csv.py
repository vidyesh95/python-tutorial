import json

from _loader import load

ex = load("t02_intermediate", "ex_13_pathlib_json_csv")


def test_write_and_read_json(tmp_path):
    path = tmp_path / "nested" / "dir" / "data.json"
    ex.write_json(path, {"b": 1, "a": [1, 2]})
    text = path.read_text(encoding="utf-8")
    assert json.loads(text) == {"a": [1, 2], "b": 1}
    assert text.index('"a"') < text.index('"b"')  # sorted keys
    assert "\n  " in text  # indent=2
    assert ex.read_json(path) == {"a": [1, 2], "b": 1}


def test_read_json_missing_file(tmp_path):
    assert ex.read_json(tmp_path / "nope.json") == {}


def test_find_files(tmp_path):
    (tmp_path / "a.csv").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.csv").write_text("x")
    (tmp_path / "dir.csv").mkdir()  # a directory with a matching name must be skipped
    found = ex.find_files(tmp_path, ".csv")
    assert found == [tmp_path / "a.csv", tmp_path / "sub" / "c.csv"]
    assert ex.find_files(tmp_path, ".md") == []


def test_read_scores(tmp_path):
    path = tmp_path / "scores.csv"
    path.write_text("name,score\nAda,91\nLinus,78\n", encoding="utf-8")
    assert ex.read_scores(path) == [
        {"name": "Ada", "score": 91},
        {"name": "Linus", "score": 78},
    ]
    path.write_text("name,score\n", encoding="utf-8")
    assert ex.read_scores(path) == []


def test_write_csv_round_trip_with_quotes(tmp_path):
    path = tmp_path / "out" / "rows.csv"
    rows = [{"name": 'Grace "Amazing"', "note": "a,b"}, {"name": "Ada", "note": ""}]
    ex.write_csv(path, rows)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "name,note"
    import csv

    with path.open(encoding="utf-8", newline="") as f:
        assert list(csv.DictReader(f)) == rows


def test_write_csv_empty(tmp_path):
    path = tmp_path / "empty.csv"
    ex.write_csv(path, [])
    assert path.exists() and path.read_text() == ""


def test_csv_to_json(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    dest = tmp_path / "out" / "out.json"
    assert ex.csv_to_json(src, dest) == 2
    assert json.loads(dest.read_text()) == {"rows": [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]}
    src.write_text("a,b\n", encoding="utf-8")
    assert ex.csv_to_json(src, dest) == 0
