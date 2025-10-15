import pytest
from database import (
    get_all_books,
)

def test_catalog_returns_list():
    """Catalog should return a list."""
    books = get_all_books()
    assert isinstance(books, list) == True

def test_catalog_item_is_dict_if_present():
    """Each catalog entry should be a dict if list is non-empty."""
    books = get_all_books()
    if books:
        assert isinstance(books[0], dict) == True

def test_catalog_has_required_keys_if_present():
    """Entries should contain required keys if present."""
    books = get_all_books()
    if books:
        b = books[0]
        for key in ["id", "title", "author", "isbn", "available_copies", "total_copies"]:
            assert (key in b) == True

def test_available_not_exceed_total_if_present():
    """available_copies <= total_copies, technical constraint."""
    books = get_all_books()
    for b in books:
        assert (b["available_copies"] <= b["total_copies"]) == True
