import pytest
from library_service import (
    search_books_in_catalog,
)

def test_search_returns_list_even_unimplemented():
    """Unimplemented search should still return a list."""
    results = search_books_in_catalog("anything", "title")
    assert isinstance(results, list) == True


def test_search_title_partial_case_insensitive(mocker):
    """Title partial + case-insensitive should match."""
    mocker.patch("library_service.get_all_books", return_value=[
        {"title": "To Kill a Mockingbird", "author": "Harper Lee", "isbn": "9780061120084"},
        {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "isbn": "9780743273565"},
    ])
    results = search_books_in_catalog("great", "title")
    assert len(results) == 1
    assert results[0]["title"] == "The Great Gatsby"


def test_search_author_partial_case_insensitive(mocker):
    """Author partial + case-insensitive should match"""
    mocker.patch("library_service.get_all_books", return_value=[
        {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "isbn": "9780743273565"},
       
    ])
    results = search_books_in_catalog("scott", "author")
    assert len(results) == 1


def test_search_isbn_exact_match(mocker):
    """ISBN search should be exact match only."""
    mocker.patch("library_service.get_all_books", return_value=[
        {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "isbn": "9780743273565"},
        {"title": "To Kill a Mockingbird", "author": "Harper Lee", "isbn": "9780061120084"},
    ])
    results = search_books_in_catalog("9780061120084", "isbn")
    assert len(results) == 1
    assert results[0]["isbn"] == "9780061120084"


def test_search_invalid_type_falls_back_to_title_author(mocker):
    """Invalid search type falls back to searching title/author (implementation behavior)."""
    mocker.patch("library_service.get_all_books", return_value=[
        {"title": "Book A", "author": "X", "isbn": "5555555555555"},
    ])
    results = search_books_in_catalog("book", "publisher")
    assert len(results) == 1
    assert results[0]["title"] == "Book A"
