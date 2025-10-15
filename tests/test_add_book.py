import pytest
from library_service import (
    add_book_to_catalog,
    get_book_by_isbn
)

def test_add_book_valid_input(mocker):
    """Test adding a book with valid input without relying on DB."""
    mocker.patch("library_service.get_book_by_isbn", return_value=None)
    mocker.patch("library_service.insert_book", return_value=True)
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 5)
    assert success is True
    assert "successfully" in message.lower()

def test_add_book_missing_title():
    """Title is required."""
    success, message = add_book_to_catalog("", "Author", "1234567890123", 3)
    assert success == False
    assert "title is required" in message.lower()

def test_add_book_title_too_long():
    """Title > 200 should fail."""
    success, message = add_book_to_catalog("X"*201, "Author", "1234567890123", 3)
    assert success == False
    assert "less than 200" in message.lower()

def test_add_book_missing_author():
    """Author is required."""
    success, message = add_book_to_catalog("Book", "", "1234567890123", 3)
    assert success == False
    assert "author is required" in message.lower()

def test_add_book_author_too_long():
    """Author > 100 should fail."""
    success, message = add_book_to_catalog("Book", "X"*101, "1234567890123", 3)
    assert success == False
    assert "less than 100" in message.lower()

def test_add_book_invalid_isbn_too_short():
    """ISBN must be exactly 13 digits."""
    success, message = add_book_to_catalog("Book", "Author", "123", 5)
    assert success == False
    assert "13 digits" in message

def test_add_book_negative_copies():
    """Total copies must be positive integer."""
    success, message = add_book_to_catalog("Book", "Author", "1234567890123", -1)
    assert success == False
    assert "positive integer" in message.lower()

def test_add_book_duplicate_isbn(mocker):
    """Duplicate ISBN should be rejected."""
    mocker.patch("library_service.get_book_by_isbn", return_value={"isbn": "1234567890123"})
    success, message = add_book_to_catalog("Book", "Author", "1234567890123", 3)
    assert success == False
    assert "already exists" in message.lower()
