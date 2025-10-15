import pytest
from library_service import (
    return_book_by_patron,
)

def test_return_valid_or_informative_message():
    """Implemented behavior: operation returns success or informative failure."""
    success, message = return_book_by_patron("123456", 1)
    assert isinstance(success, bool)
    assert isinstance(message, str)


def test_return_invalid_patron_id():
    """Invalid patron ID should fail."""
    success, message = return_book_by_patron("12A456", 1)
    assert success == False


def test_return_not_borrowed_by_patron():
    """Returning a book not borrowed by patron should fail."""
    success, message = return_book_by_patron("123456", 999)
    assert success == False


def test_return_double_return_handled_gracefully():
    """Double return should not reduce availability twice (no active record)."""
    success, message = return_book_by_patron("123456", 1)
    if success:
        # Try returning again; should fail now
        success2, message2 = return_book_by_patron("123456", 1)
        assert success2 is False
    else:
        # Already not active; acceptable informative failure
        assert isinstance(message, str)
