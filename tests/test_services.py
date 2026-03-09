"""Tests for utility service functions (validators, helpers)."""
import re
import pytest


class TestValidateEmail:
    def test_validate_email_valid(self):
        """Valid email address should return (True, None)."""
        from app.utils.validators import validate_email

        result = validate_email('user@example.com')
        assert result == (True, None), (
            f'Expected (True, None) for valid email, got {result}'
        )

    def test_validate_email_invalid(self):
        """Invalid email address should return (False, error_message)."""
        from app.utils.validators import validate_email

        is_valid, error = validate_email('not-an-email')
        assert is_valid is False, 'Invalid email must return False'
        assert error is not None, 'Invalid email must return an error message'
        assert isinstance(error, str) and len(error) > 0, (
            'Error message must be a non-empty string'
        )


class TestGenerateSlug:
    def test_generate_slug(self):
        """Slug should be lowercase, URL-safe, and end with a 4-char hex suffix."""
        from app.utils.helpers import generate_slug

        slug = generate_slug('My New Restaurant')
        assert slug.startswith('my-new-restaurant-'), (
            f'Slug must start with the normalised name, got: {slug}'
        )
        parts = slug.rsplit('-', 1)
        assert len(parts) == 2, f'Slug should have a hex suffix separated by -, got: {slug}'
        suffix = parts[1]
        assert len(suffix) == 4, f'Hex suffix must be 4 chars, got: {suffix}'
        assert re.fullmatch(r'[0-9a-f]+', suffix), (
            f'Suffix must be lowercase hex, got: {suffix}'
        )


class TestFormatCurrency:
    def test_format_currency(self):
        """Format 12.5 TND should produce '12.500 TND'."""
        from app.utils.helpers import format_currency

        result = format_currency(12.5)
        assert result == '12.500 TND', (
            f"Expected '12.500 TND', got '{result}'"
        )

    def test_format_currency_custom(self):
        """Format with custom currency should use that currency code."""
        from app.utils.helpers import format_currency

        result = format_currency(100.0, 'USD')
        assert result == '100.000 USD', (
            f"Expected '100.000 USD', got '{result}'"
        )
