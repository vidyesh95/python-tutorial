import pytest

from _loader import load

ex = load("t02_intermediate", "ex_16_regex")


def test_extract_emails():
    text = "mail ada@example.com or bob.smith@mail.co.uk!"
    assert ex.extract_emails(text) == ["ada@example.com", "bob.smith@mail.co.uk"]
    assert ex.extract_emails("no emails @ here") == []
    assert ex.extract_emails("a+tag@x.io") == ["a+tag@x.io"]


def test_parse_log_line():
    assert ex.parse_log_line("2024-03-10 12:30:00 [ERROR] disk full") == {
        "timestamp": "2024-03-10 12:30:00",
        "level": "ERROR",
        "message": "disk full",
    }
    assert ex.parse_log_line("garbage") is None
    assert ex.parse_log_line("2024-03-10 12:30:00 [info] lowercase level") is None
    assert ex.parse_log_line("2024-03-10 12:30:00 [INFO] ")["message"] == ""


def test_mask_card_numbers():
    assert (
        ex.mask_card_numbers("card 4111111111111111 ok, id 12345")
        == "card ************1111 ok, id 12345"
    )
    assert ex.mask_card_numbers("no digits") == "no digits"
    assert ex.mask_card_numbers("1234567890123") == "*********0123"  # 13 digits
    assert ex.mask_card_numbers("12345678901234567") == "12345678901234567"  # 17 digits: untouched


@pytest.mark.parametrize(
    ("snake", "camel"),
    [("user_first_name", "userFirstName"), ("name", "name"), ("a_b", "aB"), ("x_1", "x1")],
)
def test_snake_to_camel(snake, camel):
    assert ex.snake_to_camel(snake) == camel


@pytest.mark.parametrize(
    ("camel", "snake"),
    [("userFirstName", "user_first_name"), ("name", "name"), ("aB", "a_b"), ("x1Y", "x1_y")],
)
def test_camel_to_snake(camel, snake):
    assert ex.camel_to_snake(camel) == snake


@pytest.mark.parametrize(
    ("text", "valid"),
    [
        ("hello-world-2", True),
        ("a", True),
        ("Hello", False),
        ("a--b", False),
        ("-a", False),
        ("a-", False),
        ("", False),
        ("with space", False),
        ("ok\n", False),  # fullmatch must not tolerate a trailing newline
    ],
)
def test_is_valid_slug(text, valid):
    assert ex.is_valid_slug(text) is valid
