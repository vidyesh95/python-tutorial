# pathlib, json and csv
"""
pathlib.Path is the modern way to work with file paths:
    Path("a") / "b.txt"        join with /
    p.exists(), p.is_file(), p.mkdir(parents=True, exist_ok=True)
    p.read_text(), p.write_text(...), p.iterdir(), p.glob("*.csv")
    p.name, p.stem, p.suffix, p.parent, p.with_suffix(".json")
json: json.dumps/loads (strings) and json.dump/load (files).
csv:  csv.reader/writer (lists) and csv.DictReader/DictWriter (dicts).
Always open text files with newline="" for csv and encoding="utf-8".
This lesson uses a temporary directory so nothing is left behind.
"""

import csv
import json
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)

    # Example: building paths and inspecting them
    report = base / "data" / "report.csv"
    print(report.name, report.stem, report.suffix, report.parent.name)
    print(report.with_suffix(".json").name, report.exists())

    # Example: creating directories and writing/reading text
    report.parent.mkdir(parents=True, exist_ok=True)
    notes = base / "notes.txt"
    notes.write_text("line one\nline two\n", encoding="utf-8")
    print(notes.read_text(encoding="utf-8").splitlines())
    print("size:", notes.stat().st_size)

    # Example: JSON round trip
    config = {"name": "demo", "tags": ["a", "b"], "retries": 3, "debug": False, "extra": None}
    config_path = base / "config.json"
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, sort_keys=True)
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    print("round trip equal:", loaded == config)
    print(json.dumps(config))  # compact string
    print(json.dumps({"price": 9.5}, indent=2))

    # json cannot serialize everything: use default= for custom types
    from datetime import date

    print(json.dumps({"day": date(2024, 1, 2)}, default=str))

    # Example: csv with DictWriter / DictReader
    rows = [
        {"name": "Ada", "score": 91},
        {"name": "Linus", "score": 78},
        {"name": 'Grace "Amazing"', "score": 99},  # quotes are escaped for you
    ]
    with report.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "score"])
        writer.writeheader()
        writer.writerows(rows)
    print(report.read_text(encoding="utf-8"))

    with report.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            print(row["name"], int(row["score"]) + 1)  # csv values are always str

    # Example: finding files
    (base / "data" / "other.csv").write_text("a,b\n", encoding="utf-8")
    print(sorted(p.name for p in base.rglob("*.csv")))
    print(sorted(p.name for p in base.iterdir()))

    # Example: reading line by line (memory friendly)
    with notes.open(encoding="utf-8") as f:
        print([line.rstrip("\n").upper() for line in f])

    # Example: copy/rename/delete
    renamed = notes.rename(base / "renamed.txt")
    print(renamed.exists(), notes.exists())
    renamed.unlink()
    print("still exists inside the with block:", base.exists())

print("exists after the with block:", base.exists())

"""
Common mistakes
- Building paths with string concatenation or "/" in a str. Use Path / "name".
- Forgetting parents=True when creating nested directories.
- Forgetting newline="" for csv files (blank lines on Windows).
- Expecting csv to give you ints; every value is a string until you convert.
- Reading a giant file with read_text() instead of iterating lines.
- json keys are always strings: {1: "a"} comes back as {"1": "a"}.
"""

"""
Where this shows up in backend/ML work
- Loading config, secrets files and model checkpoints; writing artifacts and reports.
- JSON is the lingua franca of REST APIs (FastAPI serializes dicts and models to it).
- CSV/JSONL datasets for training and evaluation; ETL scripts.
- Tests use tmp_path (a pathlib.Path) to avoid touching real files.
"""
