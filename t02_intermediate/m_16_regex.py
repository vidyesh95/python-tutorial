# Regular Expressions
"""
The `re` module searches text with patterns. Use raw strings (r"...") so backslashes
are not treated as Python escapes.
Key pieces:
    .  any char      \d digit   \w word char   \s whitespace   \b word boundary
    *  0+   +  1+   ?  0 or 1   {2,4} range   *? lazy quantifier
    [abc] set   [^abc] negated set   a|b alternation   ^ start   $ end
    (...) capture group   (?:...) non-capturing   (?P<name>...) named group
Functions:
    re.search   first match anywhere        re.match     match at the start only
    re.fullmatch must match whole string    re.findall   list of all matches
    re.finditer  iterator of match objects  re.sub       replace   re.split  split
    re.compile   pre-build a pattern for reuse
"""

import re

text = "Order 123 shipped on 2024-03-10 to ada@example.com; order 456 on 2024-04-01."

# Example: search vs match vs fullmatch
print(bool(re.search(r"\d+", text)), bool(re.match(r"\d+", text)))
print(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", "2024-03-10")))

# Example: match objects
m = re.search(r"\d+", text)
if m:
    print(m.group(), m.start(), m.end(), m.span())

# Example: findall returns all matches (strings, or tuples if there are groups)
print(re.findall(r"\d+", text))
print(re.findall(r"(\d{4})-(\d{2})-(\d{2})", text))

# Example: groups
m = re.search(r"(\w+)@(\w+)\.com", text)
if m:
    print(m.group(0), m.group(1), m.group(2), m.groups())

# Example: named groups are self-documenting
date_re = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")
m = date_re.search(text)
if m:
    print(m.groupdict(), int(m["year"]))

# Example: finditer gives positions and groups for each match
for match in date_re.finditer(text):
    print(match.start(), match["month"])

# Example: sub replaces; the replacement can reference groups or be a function
print(re.sub(r"\d{4}-\d{2}-\d{2}", "<date>", text))
print(date_re.sub(r"\g<day>/\g<month>/\g<year>", text))
print(re.sub(r"\d+", lambda m: str(int(m.group()) * 2), "a1 b22 c3"))

# Example: split on a pattern
print(re.split(r"[,;\s]+", "a, b;c   d"))

# Example: greedy vs lazy quantifiers
html = "<b>bold</b> and <i>italic</i>"
print(re.findall(r"<.+>", html))  # greedy: one giant match
print(re.findall(r"<.+?>", html))  # lazy: individual tags

# Example: flags
print(re.findall(r"error", "Error ERROR error", flags=re.IGNORECASE))
log = "a=1\nb=2"
print(re.findall(r"^\w", log, flags=re.MULTILINE))

# Example: compile once, reuse many times (and use re.VERBOSE to document patterns)
log_line = re.compile(
    r"""
    (?P<ip>\d{1,3}(?:\.\d{1,3}){3})   # IPv4 address
    \s+\[(?P<level>[A-Z]+)\]          # level in brackets
    \s+(?P<msg>.*)                    # rest of the line
    """,
    re.VERBOSE,
)
m = log_line.match("10.0.0.1 [ERROR] disk full")
print(m.groupdict() if m else None)

# Example: escaping user-provided text
needle = "1+1=2?"
print(re.findall(re.escape(needle), "is 1+1=2? yes"))

"""
Common mistakes
- Forgetting the raw string prefix: "\d" is a warning, r"\d" is correct.
- Using re.match when you meant re.search (match anchors at the start).
- Greedy .* swallowing too much; use .*? or a negated class like [^>]*.
- Using regex for HTML/JSON/CSV; use a real parser.
- Forgetting groups change findall's output (tuples instead of strings).
- Catastrophic backtracking from nested quantifiers like (a+)+ on untrusted input.
- Not checking for None before calling .group() on a failed match.
"""

"""
Where this shows up in backend/ML work
- Parsing log lines and extracting IDs, IPs, status codes and latencies.
- Validating input formats (slugs, emails, API keys) and routing patterns (FastAPI path rules).
- Text cleaning and tokenization for NLP pipelines; redacting PII before logging.
- Pulling structured fields out of LLM output.
"""
