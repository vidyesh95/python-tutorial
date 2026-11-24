# Modules and Imports
"""
A module is simply a .py file. A package is a folder of modules (with an __init__.py). Importing lets you
reuse code from the standard library (batteries included), third-party packages or your own files.
"""

import math  # import the module, use math.sqrt
import os
import random
import sys
from collections import Counter  # import a single name
from datetime import date as Date  # import with an alias
from pathlib import Path

# Import forms
# Example
print(math.sqrt(81))
print(Counter("banana").most_common(1))
print(Date(2025, 1, 31).isoformat())
import statistics as stats  # noqa: E402  (alias for a whole module)

print(stats.mean([1, 2, 3, 4]))
# from math import *   <- avoid: pollutes the namespace and hides where names come from

# What is a module?
# Example
print(math.__name__, type(math))
print("__main__" if __name__ == "__main__" else __name__)
print(__file__.endswith("m_16_modules_imports.py"))

# if __name__ == "__main__"
"""
Every module has a __name__. When a file is run directly its name is "__main__"; when it is imported it is
the module's name. The guard below makes code run only when executed as a script, not on import.
So you can write a file that is both importable AND runnable.
"""


# Example
def main() -> None:
    print("running as a script")


if __name__ == "__main__":
    main()

# Where does Python look for modules?
# Example
print(sys.path[0] != "")  # sys.path is a list of folders searched in order
print(sys.modules["math"] is math)  # imported modules are cached in sys.modules

# Standard library tour: math
# Example
print(math.ceil(4.1), math.floor(4.9), math.pi)

# Standard library tour: random
# Example
random.seed(42)  # seed makes results reproducible
print(random.randint(1, 6))  # inclusive on both ends
print(random.choice(["rock", "paper", "scissors"]))
deck = list(range(5))
random.shuffle(deck)  # in place
print(deck, random.sample(range(100), 3), 0 <= random.random() < 1)

# Standard library tour: os and pathlib
# Example
print(type(os.getcwd()), os.name)
print(os.environ.get("DEFINITELY_NOT_SET", "fallback"))
print(
    os.path.join("a", "b", "c.txt"), os.path.basename("/x/y/z.py"), os.path.splitext("report.csv")
)
print(Path("data") / "file.txt")  # pathlib is the modern way to handle paths
print(Path("/x/y/z.py").suffix, Path("/x/y/z.py").stem, Path("/x/y/z.py").parent)

# Standard library tour: sys
# Example
print(sys.version_info >= (3, 13))
print(sys.platform in {"darwin", "linux", "win32"})
print(sys.argv[0].endswith(".py") or "run with -m")  # command-line arguments
# sys.exit(1) would stop the program with a status code

# A few more handy modules
# Example
import json  # noqa: E402
from datetime import timedelta  # noqa: E402

print(json.dumps({"a": [1, 2]}), json.loads('{"b": true}'))
print(Date(2025, 1, 31) + timedelta(days=1))

# Your own modules
"""
Put helpers in utils.py and write  from utils import helper  (same folder) or, in a package,
from mypackage.utils import helper. Use  python -m package.module  to run a module inside a package.
"""

# Common mistakes
"""
1. Naming your file like a stdlib module (random.py, json.py): it shadows the real one and breaks imports.
2. Circular imports: a imports b while b imports a. Move shared code into a third module.
3. from module import *  makes it unclear where names come from.
4. Running code at import time (prints, input, servers) - guard it with  if __name__ == "__main__".
5. ModuleNotFoundError: the package is not installed in the ACTIVE environment (see the venv/uv lesson).
"""
