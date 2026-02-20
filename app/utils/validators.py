"""Input validation and sanitization functions."""
import re

from email_validator import EmailNotValidError
from email_validator import validate_email as _validate_email_lib
from markupsafe import escape


def validate_email(email: str) -> tuple[bool, str | None]:
    """Validate an email address.

    Args:
        email: Raw email input.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        _validate_email_lib(email.strip().lower(), check_deliverability=False)
        return (True, None)
    except EmailNotValidError:
        return (False, 'Invalid email address')


def validate_phone(phone: str) -> tuple[bool, str | None]:
    """Validate a phone number (8–15 digits, optional leading +).

    Args:
        phone: Raw phone input.

    Returns:
        Tuple of (is_valid, error_message).
    """
    cleaned = phone.strip().replace(' ', '').replace('-', '')
    if re.match(r'^\+?[0-9]{8,15}$', cleaned):
        return (True, None)
    return (False, 'Invalid phone number')


def validate_price(price) -> tuple[bool, str | None]:
    """Validate a price value (non-negative, max 2 decimal places).

    Args:
        price: Raw price input (int, float, or string).

    Returns:
        Tuple of (is_valid, error_message).
    """
    error_msg = 'Price must be a non-negative number with at most 2 decimal places'
    try:
        value = float(price)
    except (TypeError, ValueError):
        return (False, error_msg)

    if value < 0:
        return (False, error_msg)

    if isinstance(price, int) or round(value, 2) == value:
        return (True, None)

    return (False, error_msg)


def sanitize_input(text: str) -> str:
    """Strip, collapse whitespace, and escape HTML entities.

    Args:
        text: Raw user input.

    Returns:
        Cleaned and escaped string.
    """
    cleaned = text.strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return str(escape(cleaned))
