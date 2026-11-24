# Strings
"""
A string (str) is an immutable sequence of characters. You create one with single, double or triple quotes.
Because strings are sequences you can index them, slice them and loop over them.
Because they are immutable, every "change" (upper(), replace(), ...) returns a NEW string.
"""

# Creating Strings
# Example
single = "single quotes"
double = "double quotes"
multi = """triple quotes
can span several lines"""
print(single, "|", double)
print(multi)

# Escape sequences and raw strings
"""
A backslash starts an escape sequence: \\n newline, \\t tab, \\\\ backslash, \\" quote.
A raw string (r"...") keeps backslashes as they are - handy for file paths and regular expressions.
"""
# Example
print("Line1\nLine2\tTabbed")
print(r"C:\new\table")  # backslashes are kept as typed

# Indexing and Slicing
"""
Indexes start at 0. Negative indexes count from the end (-1 is the last character).
Slicing uses text[start:stop:step]; stop is excluded.
"""
# Example
word = "Python"
print(word[0], word[-1])  # P n
print(word[1:4])  # yth
print(word[:2], word[2:])  # Py thon
print(word[::-1])  # nohtyP  (reversed)
print(word[::2])  # Pto

# Length, membership, concatenation, repetition
# Example
print(len(word))  # 6
print("th" in word)  # True
print("Py" + "thon", "ha" * 3)  # Python hahaha

# Common methods
"""
Strings come with many helpful methods. They never modify the original string.
"""
# Example
text = "  Hello, Python World!  "
print(text.strip())  # remove surrounding whitespace
print(text.lower(), "|", text.upper())
print(text.strip().title())
print(text.replace("World", "Learner"))
print(text.strip().startswith("Hello"), text.strip().endswith("!"))
print(text.find("Python"), text.find("Java"))  # index or -1 when missing
print(text.count("o"))

# Splitting and joining
# Example
csv_line = "apple,banana,cherry"
fruits = csv_line.split(",")
print(fruits)  # ['apple', 'banana', 'cherry']
print(" - ".join(fruits))  # apple - banana - cherry
print("one  two   three".split())  # split() with no argument splits on any whitespace

# Checking content
# Example
print("abc123".isalnum(), "abc".isalpha(), "123".isdigit(), "   ".isspace())
print("Hello".isupper(), "HELLO".isupper())

# Immutability
"""
word[0] = "J" raises TypeError. Build a new string instead.
"""
# Example
new_word = "J" + word[1:]
print(new_word)  # Jython

# Removing prefix / suffix (Python 3.9+)
# Example
print("report.txt".removesuffix(".txt"), "v1.2".removeprefix("v"))

# Iterating over a string
# Example
for ch in "abc":
    print(ch, ord(ch))  # ord() gives the Unicode code point; chr() is the reverse
print(chr(9731))

# Common mistakes
"""
1. Expecting methods to modify in place:  text.upper()  alone does nothing; use  text = text.upper().
2. Trying to assign to an index:  word[0] = "J"  raises TypeError.
3. Building big strings with += inside loops; collect pieces in a list and use "".join(pieces).
4. Mixing str and int:  "age: " + 5  raises TypeError; use f"age: {5}" or str(5).
5. Forgetting that slicing never raises IndexError but indexing does:  "abc"[10]  fails, "abc"[10:] is "".
"""
