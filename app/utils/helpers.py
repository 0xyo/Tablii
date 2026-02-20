"""General-purpose helper functions."""
import random
import re
import secrets
import string


def generate_slug(name: str) -> str:
    """Create a URL-safe slug from a name with a random hex suffix.

    Args:
        name: Human-readable name (e.g. "My Restaurant").

    Returns:
        Slugified string like ``my-restaurant-a3f1``.
    """
    base = name.lower()
    base = re.sub(r'[^a-z0-9]+', '-', base)
    base = re.sub(r'-+', '-', base)
    base = base.strip('-')
    return f'{base}-{secrets.token_hex(2)}'


def format_currency(amount: float, currency: str = 'TND') -> str:
    """Format a monetary amount for display.

    Args:
        amount: Numeric value.
        currency: ISO currency code (default TND — 3 decimal places).

    Returns:
        Formatted string like ``12.500 TND``.
    """
    return f'{amount:.3f} {currency}'


def generate_random_token(length: int = 32) -> str:
    """Generate a URL-safe random token.

    Args:
        length: Number of random bytes (output is base64-encoded).

    Returns:
        URL-safe token string.
    """
    return secrets.token_urlsafe(length)


def generate_order_number() -> str:
    """Generate a short order reference code.

    Returns:
        String like ``#A7K2``.
    """
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f'#{code}'
