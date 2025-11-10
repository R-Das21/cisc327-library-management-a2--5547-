import pytest
from library_service import (
    borrow_book_by_patron,
)

def test_borrow_valid_flow(mocker):
    """Happy path: valid patron, available book, DB ops succeed."""
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1, "title": "1984", "available_copies": 2})
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=0)
    mocker.patch("services.library_service.insert_borrow_record", return_value=True)
    mocker.patch("services.library_service.update_book_availability", return_value=True)
    success, message = borrow_book_by_patron("123456", 1)
    assert success == True
    assert "successfully borrowed" in message.lower()

def test_borrow_invalid_patron_non_digit():
    """Patron ID must be exactly 6 digits."""
    success, message = borrow_book_by_patron("12A456", 1)
    assert success == False
    assert "invalid patron" in message.lower()

def test_borrow_invalid_patron_wrong_len():
    """Patron ID must be exactly 6 digits."""
    success, message = borrow_book_by_patron("12345", 1)
    assert success == False
    assert "invalid patron" in message.lower()

def test_borrow_book_not_found(mocker):
    """Book must exist."""
    mocker.patch("services.library_service.get_book_by_id", return_value=None)
    success, message = borrow_book_by_patron("123456", 99)
    assert success == False
    assert "not found" in message.lower()

def test_borrow_unavailable_book(mocker):
    """Book must be available."""
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 2, "title": "1984", "available_copies": 0})
    success, message = borrow_book_by_patron("123456", 2)
    assert success == False
    assert "not available" in message.lower()

def test_borrow_limit_exceeded_over_5(mocker):
    """Borrowing limit is max 5."""
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1, "title": "1984", "available_copies": 1})
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=6)
    success, message = borrow_book_by_patron("123456", 1)
    assert success == False
    assert "maximum borrowing limit" in message.lower()

def test_borrow_limit_boundary_exactly_5_current_impl(mocker):
    """At exactly 5, requirement says should be blocked; current impl may allow."""
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1, "title": "1984", "available_copies": 1})
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=5)
    success, message = borrow_book_by_patron("123456", 1)
    assert success == False
    assert "maximum borrowing limit" in message.lower()

def test_borrow_db_failure_insert(mocker):
    """DB failure when inserting borrow record should fail."""
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1, "title": "1984", "available_copies": 1})
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=0)
    mocker.patch("services.library_service.insert_borrow_record", return_value=False)
    success, message = borrow_book_by_patron("123456", 1)
    assert success == False
    assert "creating borrow record" in message.lower()

def test_borrow_db_failure_update_availability(mocker):
    """DB failure when updating availability should fail."""
    mocker.patch("services.library_service.get_book_by_id", return_value={"id": 1, "title": "1984", "available_copies": 1})
    mocker.patch("services.library_service.get_patron_borrow_count", return_value=0)
    mocker.patch("services.library_service.insert_borrow_record", return_value=True)
    mocker.patch("services.library_service.update_book_availability", return_value=False)
    success, message = borrow_book_by_patron("123456", 1)
    assert success == False
    assert "updating book availability" in message.lower()
