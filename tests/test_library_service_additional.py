from datetime import datetime, timedelta

import pytest
from unittest.mock import Mock

from library_service import (
    calculate_late_fee_for_book,
    get_patron_status_report,
    pay_late_fees,
    refund_late_fee_payment,
    return_book_by_patron,
)
from services import library_service as lib


def test_parse_dt_handles_datetime():
    now = datetime.now()
    assert lib._parse_dt(now) is now


def test_parse_dt_parses_string_to_datetime():
    parsed = lib._parse_dt("2024-10-05")
    assert isinstance(parsed, datetime)
    assert parsed.date().isoformat() == "2024-10-05"


def test_parse_dt_invalid_returns_none():
    assert lib._parse_dt("not-a-date") is None


def test_parse_dt_iso_with_fractional_seconds():
    parsed = lib._parse_dt("2024-10-05T12:30:45.123456")
    assert isinstance(parsed, datetime)
    assert parsed.microsecond == 123456


@pytest.mark.parametrize(
    "value, expected",
    [(10.235, 10.23), ("bad", 0.0)],
)
def test_monetize_formats_values(value, expected):
    assert lib._monetize(value) == expected


def test_compute_fee_handles_various_branches():
    now = datetime.now()
    # Missing due date returns zeros
    assert lib._compute_fee_from_due_and_end(None, now) == (0.0, 0)
    # Not overdue yet also returns zeros
    assert lib._compute_fee_from_due_and_end(now, now) == (0.0, 0)
    # Overdue more than cap hits maximum fee
    overdue_due = now - timedelta(days=30)
    fee, days = lib._compute_fee_from_due_and_end(overdue_due, now)
    assert fee == 15.0
    assert days == 30


def test_return_book_success_with_fee(mocker):
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Mock Title"})
    mocker.patch(
        "services.library_service.get_patron_borrowed_books",
        return_value=[{"book_id": 1, "due_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")}],
    )
    mocker.patch("services.library_service._compute_fee_from_due_and_end", return_value=(3.50, 4))
    mocker.patch("services.library_service.update_borrow_record_return_date", return_value=True)
    mocker.patch("services.library_service.update_book_availability", return_value=True)

    success, message = return_book_by_patron("123456", 1)

    assert success is True
    assert "Late fee: $3.50" in message


def test_return_book_no_active_record(mocker):
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Mock"})
    mocker.patch("services.library_service.get_patron_borrowed_books", return_value=[])

    success, message = return_book_by_patron("123456", 1)

    assert success is False
    assert message == "No active borrow record found for this patron and book."


def test_return_book_update_return_failure(mocker):
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Mock"})
    mocker.patch(
        "services.library_service.get_patron_borrowed_books",
        return_value=[{"book_id": 1, "due_date": datetime.now().strftime("%Y-%m-%d")}],
    )
    mocker.patch("services.library_service._compute_fee_from_due_and_end", return_value=(0.0, 0))
    mocker.patch("services.library_service.update_borrow_record_return_date", return_value=False)

    success, message = return_book_by_patron("123456", 1)

    assert success is False
    assert message == "Database error while recording the return."


def test_return_book_update_availability_failure(mocker):
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Mock"})
    mocker.patch(
        "services.library_service.get_patron_borrowed_books",
        return_value=[{"book_id": 1, "due_date": datetime.now().strftime("%Y-%m-%d")}],
    )
    mocker.patch("services.library_service._compute_fee_from_due_and_end", return_value=(0.0, 0))
    mocker.patch("services.library_service.update_borrow_record_return_date", return_value=True)
    mocker.patch("services.library_service.update_book_availability", return_value=False)

    success, message = return_book_by_patron("123456", 1)

    assert success is False
    assert message == "Database error while updating book availability."


def test_calculate_late_fee_not_overdue(mocker):
    mocker.patch(
        "services.library_service.get_patron_borrowed_books",
        return_value=[{"book_id": 1, "due_date": datetime.now().strftime("%Y-%m-%d")}],
    )
    mocker.patch("services.library_service._compute_fee_from_due_and_end", return_value=(0.0, 0))

    result = calculate_late_fee_for_book("123456", 1)

    assert result["status"] == "not_overdue"
    assert result["fee_amount"] == 0.0


def test_calculate_late_fee_overdue(mocker):
    mocker.patch(
        "services.library_service.get_patron_borrowed_books",
        return_value=[{"book_id": 1, "due_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")}],
    )
    mocker.patch("services.library_service._compute_fee_from_due_and_end", return_value=(2.5, 5))

    result = calculate_late_fee_for_book("123456", 1)

    assert result["status"] == "ok"
    assert result["fee_amount"] == 2.5
    assert result["days_overdue"] == 5


def _dummy_connection(rows):
    class DummyCursor:
        def __init__(self, data):
            self._data = data

        def fetchall(self):
            return self._data

    class DummyConnection:
        def __init__(self, data):
            self._data = data

        def execute(self, *_args, **_kwargs):
            return DummyCursor(self._data)

        def close(self):
            return None

    return DummyConnection(rows)


def test_get_patron_status_report_populates_history(mocker):
    current_borrows = [
        {
            "book_id": 1,
            "title": "Current Book",
            "due_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        }
    ]
    history_rows = [
        {
            "book_id": 1,
            "title": "Past Book",
            "borrow_date": "2023-01-01",
            "due_date": "2023-01-10",
            "return_date": "2023-01-12",
        }
    ]
    mocker.patch("services.library_service.get_patron_borrowed_books", return_value=current_borrows)
    mocker.patch("services.library_service._compute_fee_from_due_and_end", return_value=(1.5, 2))
    mocker.patch("database.get_db_connection", return_value=_dummy_connection(history_rows))

    report = get_patron_status_report("123456")

    assert report["current_borrow_count"] == 1
    assert report["total_late_fees"] == 1.5
    assert report["history"] and report["history"][0]["title"] == "Past Book"


def test_get_patron_status_report_handles_db_failure(mocker):
    mocker.patch("services.library_service.get_patron_borrowed_books", return_value=[])
    mocker.patch("database.get_db_connection", side_effect=RuntimeError("db down"))

    report = get_patron_status_report("123456")

    assert report["history"] == []
    assert report["status"] == "ok"


def test_pay_late_fees_missing_fee_info(mocker):
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={})

    success, message, txn = pay_late_fees("123456", 1, payment_gateway=Mock(spec=lib.PaymentGateway))

    assert success is False
    assert message == "Unable to calculate late fees."
    assert txn is None


def test_pay_late_fees_creates_gateway_when_not_provided(mocker):
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={"fee_amount": 5.0})
    mocker.patch("services.library_service.get_book_by_id", return_value={"title": "Auto Gateway"})
    gateway_instance = Mock(spec=lib.PaymentGateway)
    gateway_instance.process_payment.return_value = (True, "txn_auto", "Approved")
    mocker.patch("services.library_service.PaymentGateway", return_value=gateway_instance)

    success, message, txn = pay_late_fees("123456", 1)

    assert success is True
    assert txn == "txn_auto"
    gateway_instance.process_payment.assert_called_once()


def test_refund_late_fee_gateway_failure(mocker):
    gateway_mock = Mock(spec=lib.PaymentGateway)
    gateway_mock.refund_payment.return_value = (False, "Declined")

    success, message = refund_late_fee_payment("txn_123", 5.0, payment_gateway=gateway_mock)

    assert success is False
    assert message == "Refund failed: Declined"


def test_refund_late_fee_gateway_exception(mocker):
    gateway_mock = Mock(spec=lib.PaymentGateway)
    gateway_mock.refund_payment.side_effect = RuntimeError("gateway offline")

    success, message = refund_late_fee_payment("txn_123", 5.0, payment_gateway=gateway_mock)

    assert success is False
    assert message == "Refund processing error: gateway offline"


def test_refund_late_fee_creates_gateway_when_not_provided(mocker):
    gateway_instance = Mock(spec=lib.PaymentGateway)
    gateway_instance.refund_payment.return_value = (True, "Refund OK")
    mocker.patch("services.library_service.PaymentGateway", return_value=gateway_instance)

    success, message = refund_late_fee_payment("txn_999", 4.0)

    assert success is True
    assert message == "Refund OK"
    gateway_instance.refund_payment.assert_called_once_with("txn_999", 4.0)


@pytest.mark.parametrize(
    "title, author, isbn, total_copies, expected_message",
    [
        ("   ", "Author", "1234567890123", 1, "Title is required."),
        ("Title", "   ", "1234567890123", 1, "Author is required."),
        ("Title", "Author", "123", 1, "ISBN must be exactly 13 digits."),
        ("Title", "Author", "1234567890123", 0, "Total copies must be a positive integer."),
    ],
)
def test_add_book_validation_branches(title, author, isbn, total_copies, expected_message):
    success, message = lib.add_book_to_catalog(title, author, isbn, total_copies)
    assert success is False
    assert message == expected_message
