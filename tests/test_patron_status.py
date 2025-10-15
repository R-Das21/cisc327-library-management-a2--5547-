import pytest
from library_service import (
    get_patron_status_report,
)

def test_status_returns_structured_report():
    """Implemented report returns structured dict with expected keys."""
    result = get_patron_status_report("123456")
    assert isinstance(result, dict) is True
    for key in ["patron_id", "current_borrows", "current_borrow_count", "total_late_fees", "history", "status"]:
        assert key in result


def test_status_includes_current_borrows_and_due_dates():
    """Expect 'current_borrows' list with items including due dates."""
    report = get_patron_status_report("123456")
    assert "current_borrows" in report
    assert isinstance(report["current_borrows"], list) is True
    if report["current_borrows"]:
        item = report["current_borrows"][0]
        for key in ["book_id", "title", "due_date", "days_overdue", "late_fee"]:
            assert key in item


def test_status_includes_total_late_fees_and_borrow_count():
    """Expect late fees total and current borrow count."""
    report = get_patron_status_report("123456")
    assert "total_late_fees" in report
    assert "current_borrow_count" in report


def test_status_includes_history_list():
    """Expect borrow/return history list."""
    report = get_patron_status_report("123456")
    assert "history" in report
    assert isinstance(report["history"], list) is True

    
def test_status_invalid_patron_returns_structured_error():
    """Invalid patron ID returns structured dict with status flag."""
    result = get_patron_status_report("ABCDEF")
    assert isinstance(result, dict) is True
    assert result.get("status") == "invalid_patron_id"
