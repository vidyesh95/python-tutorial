"""Exercise 04 - Strings.

Tasks:
1. is_palindrome: ignore case, spaces and punctuation.
2. count_vowels: count a, e, i, o, u (any case).
3. reverse_words: reverse the order of the words in a sentence.
4. truncate: shorten text to a maximum length, ending with "..." when shortened.
"""


def is_palindrome(text: str) -> bool:
    """Return True if ``text`` reads the same backwards, ignoring case and non-alphanumerics.

    Examples:
        is_palindrome("Racecar") -> True
        is_palindrome("A man, a plan, a canal: Panama") -> True
        is_palindrome("hello") -> False
        is_palindrome("") -> True
    """
    cleaned = [ch.lower() for ch in text if ch.isalnum()]
    return cleaned == cleaned[::-1]


def count_vowels(text: str) -> int:
    """Count the vowels (a, e, i, o, u) in ``text``, case-insensitive.

    Examples:
        count_vowels("Hello World") -> 3
        count_vowels("rhythm") -> 0
        count_vowels("AEIOU") -> 5
    """
    return sum(1 for ch in text.lower() if ch in "aeiou")


def reverse_words(sentence: str) -> str:
    """Reverse the word order; words are separated by any whitespace, output uses single spaces.

    Examples:
        reverse_words("one two three") -> "three two one"
        reverse_words("  hello   world ") -> "world hello"
        reverse_words("") -> ""
    """
    return " ".join(reversed(sentence.split()))


def truncate(text: str, max_len: int) -> str:
    """Return ``text`` unchanged if it fits in ``max_len``; otherwise cut it so that the result,
    INCLUDING a trailing "...", is exactly ``max_len`` characters. Assume ``max_len >= 3``.

    Examples:
        truncate("hello", 10) -> "hello"
        truncate("hello world", 8) -> "hello..."
        truncate("abc", 3) -> "abc"
    """
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
