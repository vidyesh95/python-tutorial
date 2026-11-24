# Testing with pytest
"""
pytest runs functions named test_* in files named test_*.py.
Core ideas:
    assert expr                     plain asserts, with rich failure messages
    pytest.raises(Err, match=...)   expect an exception
    @pytest.fixture                 reusable setup; request it by naming it as an argument
    @pytest.mark.parametrize        run one test over many inputs
    tmp_path                        built-in fixture: a fresh temporary directory (Path)
    monkeypatch                     built-in fixture: safely patch env vars, attributes, dicts
    capsys / caplog                 capture printed output / log records
This lesson runs WITHOUT pytest. It defines a small function and shows, in strings and
docstrings, how its tests would look. Run real tests with:
    uv run pytest t02_intermediate -k comprehensions
    uv run pytest -x -q          # stop at first failure
    uv run pytest -k "name"      # filter by name
"""

import os


# Example: a small function under test
def slugify(title: str) -> str:
    """Lowercase, trim, replace runs of non-alphanumerics with a single '-'."""
    if not isinstance(title, str):
        raise TypeError("title must be a string")
    chars: list[str] = []
    for ch in title.strip().lower():
        if ch.isalnum():
            chars.append(ch)
        elif chars and chars[-1] != "-":
            chars.append("-")
    return "".join(chars).strip("-")


print(slugify("  Hello, World!  "), slugify("A -- B"), repr(slugify("")))

# Example: how the tests would look (kept in a string so this file runs without pytest)
EXAMPLE_TESTS = """
import pytest
from mymodule import slugify

# 1. Plain asserts, one behaviour per test
def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"

# 2. parametrize: one test body, many cases (edge cases belong here)
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  padded  ", "padded"),
        ("A -- B", "a-b"),
        ("", ""),
        ("!!!", ""),
    ],
)
def test_slugify_cases(raw, expected):
    assert slugify(raw) == expected

# 3. pytest.raises for expected errors
def test_slugify_rejects_non_str():
    with pytest.raises(TypeError, match="must be a string"):
        slugify(123)

# 4. fixtures: shared setup, with teardown after yield
@pytest.fixture
def sample_file(tmp_path):
    path = tmp_path / "titles.txt"
    path.write_text("Hello World\\nFoo Bar\\n")
    return path

def test_slugify_file(sample_file):
    lines = sample_file.read_text().splitlines()
    assert [slugify(t) for t in lines] == ["hello-world", "foo-bar"]

# 5. monkeypatch: change the environment safely (restored after the test)
def test_reads_env(monkeypatch):
    monkeypatch.setenv("APP_MODE", "test")
    assert os.environ["APP_MODE"] == "test"

# 6. caplog / capsys: assert on logs and printed output
def test_logs(caplog):
    caplog.set_level("INFO")
    logging.getLogger("x").info("hello")
    assert "hello" in caplog.text
"""
print(EXAMPLE_TESTS.count("def test_"), "example tests shown")


# Example: what monkeypatch does conceptually (set, use, restore)
def get_mode() -> str:
    return os.environ.get("APP_MODE", "prod")


print("before:", get_mode())
os.environ["APP_MODE"] = "test"
print("patched:", get_mode())
del os.environ["APP_MODE"]  # monkeypatch undoes this automatically
print("restored:", get_mode())


# Example: the arrange / act / assert shape of a good test
def test_slugify_shape() -> None:
    value = "  Python 3.15  "  # arrange
    result = slugify(value)  # act
    assert result == "python-3-13"  # assert


test_slugify_shape()  # a test is just a function; pytest finds and calls it for you
print("manual test passed")

"""
Common mistakes
- Tests that depend on each other or on execution order. Each test must stand alone.
- Testing implementation details instead of behaviour.
- Writing to real files/DBs or hitting the network in unit tests. Use tmp_path,
  monkeypatch and fakes.
- Only testing the happy path. Add empty input, None, boundaries, bad types.
- Giant tests with many unrelated asserts; failures become hard to read.
- Mutable state shared through module-level variables instead of fixtures.
- Forgetting that fixture scope defaults to "function" (fresh per test).
"""

"""
Where this shows up in backend/ML work
- FastAPI apps are tested with TestClient and dependency overrides (fixtures + fakes).
- CI runs `pytest` on every pull request; failing tests block deploys.
- ML code: parametrized tests for preprocessing, golden-file tests for model outputs.
- monkeypatch swaps real LLM/HTTP clients for deterministic fakes.
"""
