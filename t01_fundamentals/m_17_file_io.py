# File I/O
"""
Use open() to read and write files. ALWAYS use it with a `with` block (a context manager) so the file is
closed for you, even if an error occurs. Always pass encoding="utf-8" for text files.

Modes:  "r" read (default)   "w" write (truncates!)   "a" append   "x" create, fail if exists
        add "b" for binary ("rb", "wb"), add "+" to read and write.
All examples write into a temporary directory so nothing is left in your repo.
"""

import csv
import json
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    notes = folder / "notes.txt"

    # Writing text
    # Example
    with open(notes, "w", encoding="utf-8") as f:
        f.write("first line\n")  # write() does NOT add a newline for you
        f.write("second line\n")
        f.writelines(["third line\n", "fourth line\n"])

    # Reading text
    # Example
    with open(notes, encoding="utf-8") as f:
        whole = f.read()
    print(repr(whole))

    with open(notes, encoding="utf-8") as f:
        print(f.readline().rstrip())  # one line
        print(f.readlines())  # the remaining lines as a list

    # Looping over a file (memory friendly: one line at a time)
    # Example
    with open(notes, encoding="utf-8") as f:
        for number, line in enumerate(f, start=1):
            print(number, line.rstrip("\n"))

    # Appending
    # Example
    with open(notes, "a", encoding="utf-8") as f:
        f.write("appended\n")
    print(len(notes.read_text(encoding="utf-8").splitlines()), "lines now")

    # Mode "w" erases existing content!
    # Example
    scratch = folder / "scratch.txt"
    scratch.write_text("old", encoding="utf-8")
    scratch.write_text("new", encoding="utf-8")
    print(scratch.read_text(encoding="utf-8"))

    # Mode "x" refuses to overwrite
    # Example
    try:
        with open(scratch, "x", encoding="utf-8") as f:
            f.write("never")
    except FileExistsError:
        print("scratch.txt already exists")

    # Handling a missing file
    # Example
    try:
        open(folder / "missing.txt", encoding="utf-8")
    except FileNotFoundError as err:
        print("missing:", err.filename.endswith("missing.txt"))

    # pathlib shortcuts
    # Example
    print(notes.exists(), notes.is_file(), notes.name, notes.suffix)
    print(sorted(p.name for p in folder.iterdir()))
    sub = folder / "sub" / "deeper"
    sub.mkdir(parents=True, exist_ok=True)
    print(sub.is_dir())
    scratch.unlink()  # delete a file

    # Binary files
    # Example
    blob = folder / "data.bin"
    blob.write_bytes(bytes([0, 1, 2, 255]))
    print(list(blob.read_bytes()))

    # JSON files
    # Example
    config = folder / "config.json"
    with open(config, "w", encoding="utf-8") as f:
        json.dump({"name": "demo", "tags": ["a", "b"]}, f, indent=2)
    with open(config, encoding="utf-8") as f:
        print(json.load(f))

    # CSV files (newline="" is required by the csv module)
    # Example
    table = folder / "people.csv"
    with open(table, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age"])
        writer.writerows([["Ann", 30], ["Bob", 25]])
    with open(table, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            print(row)

print("temp folder removed:", not folder.exists())

# Common mistakes
"""
1. Forgetting to close a file (use `with`).
2. Opening with "w" when you meant "a" - it wipes the file.
3. Not specifying encoding="utf-8" - behaviour then depends on the operating system.
4. Reading a huge file with read() when a line-by-line loop would do.
5. Forgetting that write() needs a str (not an int) and that you must add "\\n" yourself.
6. Relative paths depend on the CURRENT working directory, not the location of your script
   (use Path(__file__).parent for paths next to the script).
"""
