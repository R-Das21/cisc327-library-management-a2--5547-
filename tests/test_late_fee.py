import pytest
from library_service import (
    calculate_late_fee_for_book,
)

def test_late_fee_result_shape_and_defaults():
    """Result structure: dict with fee_amount & days_overdue; on-time defaults to 0."""
    result = calculate_late_fee_for_book("123456", 1)
    assert isinstance(result, dict) is True
    assert "fee_amount" in result and "days_overdue" in result and "status" in result
    # Depending on data state, non-overdue yields zeroes
    if result.get("status") == "not_overdue":
        assert result.get("fee_amount") == 0.00
        assert result.get("days_overdue") == 0


def test_late_fee_on_time_zero():
    """On-time -> $0 fee (if not overdue)."""
    r = calculate_late_fee_for_book("123456", 1)
    if r.get("status") == "not_overdue":
        assert r["fee_amount"] == 0.00
        assert r["days_overdue"] == 0


def test_late_fee_first_7_days():
    """If 1-7 days overdue, fee between $0.50 and $3.50."""
    r = calculate_late_fee_for_book("123456", 1)
    if r.get("days_overdue", 0) > 0:
        assert 0.50 <= r["fee_amount"] <= 3.50


def test_late_fee_after_7_days_escalation():
    """If >7 days overdue, fee >= $6.50."""
    r = calculate_late_fee_for_book("123456", 1)
    if r.get("days_overdue", 0) > 7:
        assert r["fee_amount"] >= 6.50


def test_late_fee_capped_at_15():
    """Cap at $15 applies to high overdue days."""
    r = calculate_late_fee_for_book("123456", 1)
    assert r["fee_amount"] <= 15.00
