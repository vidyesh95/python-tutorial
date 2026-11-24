from _loader import load

ex = load("t01_fundamentals", "ex_04_strings")


def test_is_palindrome():
    assert ex.is_palindrome("Racecar") is True
    assert ex.is_palindrome("A man, a plan, a canal: Panama") is True
    assert ex.is_palindrome("hello") is False
    assert ex.is_palindrome("") is True


def test_count_vowels():
    assert ex.count_vowels("Hello World") == 3
    assert ex.count_vowels("rhythm") == 0
    assert ex.count_vowels("AEIOU") == 5
    assert ex.count_vowels("") == 0


def test_reverse_words():
    assert ex.reverse_words("one two three") == "three two one"
    assert ex.reverse_words("  hello   world ") == "world hello"
    assert ex.reverse_words("") == ""
    assert ex.reverse_words("solo") == "solo"


def test_truncate():
    assert ex.truncate("hello", 10) == "hello"
    assert ex.truncate("hello world", 8) == "hello..."
    assert ex.truncate("abc", 3) == "abc"
    assert len(ex.truncate("x" * 50, 20)) == 20
