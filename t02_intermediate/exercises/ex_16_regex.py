"""Exercise 16: Regular expressions.

Tasks
1. extract_emails: findall.
2. parse_log_line: named groups into a dict.
3. mask_card_numbers: sub with a function.
4. snake_to_camel / camel_to_snake: sub conversions.
5. is_valid_slug: fullmatch.

Run: uv run pytest t02_intermediate -k regex
"""

import re

EMAIL_RE = re.compile("[\\w.+-]+@[\\w-]+(?:\\.[\\w-]+)+")
LOG_RE = re.compile(
    "^(?P<timestamp>\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}) \\[(?P<level>[A-Z]+)\\] (?P<message>.*)$"
)
SLUG_RE = re.compile("[a-z0-9]+(?:-[a-z0-9]+)*")


def extract_emails(text: str) -> list[str]:
    """Return all email addresses in text, in order.

    >>> extract_emails("mail ada@example.com or bob.smith@mail.co.uk!")
    ['ada@example.com', 'bob.smith@mail.co.uk']
    """
    raise NotImplementedError


def parse_log_line(line: str) -> dict[str, str] | None:
    """Parse '2024-03-10 12:30:00 [ERROR] disk full' into
    {'timestamp': '2024-03-10 12:30:00', 'level': 'ERROR', 'message': 'disk full'}.

    Return None if the line does not match.
    """
    raise NotImplementedError


def mask_card_numbers(text: str) -> str:
    """Replace every standalone run of 13-16 digits with '*' x (len-4) + last four digits.

    >>> mask_card_numbers("card 4111111111111111 ok, id 12345")
    'card ************1111 ok, id 12345'
    """
    raise NotImplementedError


def snake_to_camel(text: str) -> str:
    """'user_first_name' -> 'userFirstName'.

    >>> snake_to_camel("user_first_name")
    'userFirstName'
    """
    raise NotImplementedError


def camel_to_snake(text: str) -> str:
    """'userFirstName' -> 'user_first_name'.

    >>> camel_to_snake("userFirstName")
    'user_first_name'
    """
    raise NotImplementedError


def is_valid_slug(text: str) -> bool:
    """A slug is lowercase letters/digits separated by single hyphens
    (no leading, trailing or double hyphens). Use fullmatch.

    >>> is_valid_slug("hello-world-2"), is_valid_slug("Hello"), is_valid_slug("a--b")
    (True, False, False)
    """
    raise NotImplementedError
