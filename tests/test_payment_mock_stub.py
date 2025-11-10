from unittest.mock import Mock

import pytest

from library_service import pay_late_fees, refund_late_fee_payment
from payment_service import PaymentGateway


def test_pay_late_fees_successful_payment(mocker):
    mocker.patch(
    "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 7.50},
    )
    mocker.patch(
    "services.library_service.get_book_by_id",
        return_value={"title": "The Testing Tales"},
    )
    gateway_mock = Mock(spec=PaymentGateway)
    gateway_mock.process_payment.return_value = (
        True,
        "txn_123456_success",
        "Gateway approved",
    )

    success, message, transaction_id = pay_late_fees(
        patron_id="123456",
        book_id=42,
        payment_gateway=gateway_mock,
    )

    assert success is True
    assert "Payment successful" in message
    assert transaction_id == "txn_123456_success"
    gateway_mock.process_payment.assert_called_once()
    gateway_mock.process_payment.assert_called_with(
        patron_id="123456",
        amount=7.50,
        description="Late fees for 'The Testing Tales'",
    )


def test_pay_late_fees_declined_by_gateway(mocker):
    mocker.patch(
    "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 9.25},
    )
    mocker.patch(
    "services.library_service.get_book_by_id",
        return_value={"title": "Declined Adventures"},
    )
    gateway_mock = Mock(spec=PaymentGateway)
    gateway_mock.process_payment.return_value = (
        False,
        "",
        "Card declined",
    )

    success, message, transaction_id = pay_late_fees(
        patron_id="654321",
        book_id=7,
        payment_gateway=gateway_mock,
    )

    assert success is False
    assert message == "Payment failed: Card declined"
    assert transaction_id is None
    gateway_mock.process_payment.assert_called_once()
    gateway_mock.process_payment.assert_called_with(
        patron_id="654321",
        amount=9.25,
        description="Late fees for 'Declined Adventures'",
    )


def test_pay_late_fees_invalid_patron_id():
    gateway_mock = Mock(spec=PaymentGateway)

    success, message, transaction_id = pay_late_fees(
        patron_id="12AB56",
        book_id=5,
        payment_gateway=gateway_mock,
    )

    assert success is False
    assert message == "Invalid patron ID. Must be exactly 6 digits."
    assert transaction_id is None
    gateway_mock.process_payment.assert_not_called()


def test_pay_late_fees_zero_amount(mocker):
    mocker.patch(
    "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 0.0},
    )
    mocker.patch(
    "services.library_service.get_book_by_id",
        return_value={"title": "Zero Charge"},
    )
    gateway_mock = Mock(spec=PaymentGateway)

    success, message, transaction_id = pay_late_fees(
        patron_id="222333",
        book_id=9,
        payment_gateway=gateway_mock,
    )

    assert success is False
    assert message == "No late fees to pay for this book."
    assert transaction_id is None
    gateway_mock.process_payment.assert_not_called()


def test_pay_late_fees_network_error(mocker):
    mocker.patch(
    "services.library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 4.10},
    )
    mocker.patch(
    "services.library_service.get_book_by_id",
        return_value={"title": "Network Adventures"},
    )
    gateway_mock = Mock(spec=PaymentGateway)
    gateway_mock.process_payment.side_effect = Exception("Network error")

    success, message, transaction_id = pay_late_fees(
        patron_id="135790",
        book_id=3,
        payment_gateway=gateway_mock,
    )

    assert success is False
    assert message == "Payment processing error: Network error"
    assert transaction_id is None
    gateway_mock.process_payment.assert_called_once_with(
        patron_id="135790",
        amount=4.10,
        description="Late fees for 'Network Adventures'",
    )


def test_refund_late_fee_success():
    gateway_mock = Mock(spec=PaymentGateway)
    gateway_mock.refund_payment.return_value = (
        True,
        "Refund processed",
    )

    success, message = refund_late_fee_payment(
        transaction_id="txn_98765",
        amount=5.75,
        payment_gateway=gateway_mock,
    )

    assert success is True
    assert message == "Refund processed"
    gateway_mock.refund_payment.assert_called_once()
    gateway_mock.refund_payment.assert_called_with("txn_98765", 5.75)


def test_refund_late_fee_invalid_transaction_id():
    gateway_mock = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment(
        transaction_id="invalid",
        amount=4.25,
        payment_gateway=gateway_mock,
    )

    assert success is False
    assert message == "Invalid transaction ID."
    gateway_mock.refund_payment.assert_not_called()


@pytest.mark.parametrize(
    "amount, expected_message",
    [
        (-3.00, "Refund amount must be greater than 0."),
        (0.00, "Refund amount must be greater than 0."),
        (20.00, "Refund amount exceeds maximum late fee."),
    ],
)
def test_refund_late_fee_invalid_amounts(amount, expected_message):
    gateway_mock = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment(
        transaction_id="txn_55555",
        amount=amount,
        payment_gateway=gateway_mock,
    )

    assert success is False
    assert message == expected_message
    gateway_mock.refund_payment.assert_not_called()
