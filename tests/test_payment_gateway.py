import pytest

from services.payment_service import PaymentGateway


@pytest.fixture(autouse=True)
def patch_sleep(mocker):
    mocker.patch("services.payment_service.time.sleep", return_value=None)


@pytest.fixture
def frozen_time(mocker):
    mocker.patch("services.payment_service.time.time", return_value=1_700_000_000)


def test_process_payment_invalid_amount():
    gateway = PaymentGateway()
    success, txn, message = gateway.process_payment("123456", -5.0)
    assert success is False
    assert txn == ""
    assert "Invalid amount" in message


def test_process_payment_exceeds_limit(frozen_time):
    gateway = PaymentGateway()
    success, txn, message = gateway.process_payment("123456", 2000.0)
    assert success is False
    assert txn == ""
    assert "exceeds limit" in message


def test_process_payment_invalid_patron():
    gateway = PaymentGateway()
    success, txn, message = gateway.process_payment("ABC", 10.0)
    assert success is False
    assert txn == ""
    assert "Invalid patron ID" in message


def test_process_payment_success(frozen_time):
    gateway = PaymentGateway()
    success, txn, message = gateway.process_payment("123456", 10.0, description="Late fees")
    assert success is True
    assert txn.startswith("txn_123456_")
    assert "processed successfully" in message


def test_refund_payment_invalid_transaction():
    gateway = PaymentGateway()
    success, message = gateway.refund_payment("bad", 5.0)
    assert success is False
    assert message == "Invalid transaction ID"


def test_refund_payment_invalid_amount():
    gateway = PaymentGateway()
    success, message = gateway.refund_payment("txn_123", 0.0)
    assert success is False
    assert message == "Invalid refund amount"


def test_refund_payment_success(frozen_time):
    gateway = PaymentGateway()
    success, message = gateway.refund_payment("txn_123", 5.0)
    assert success is True
    assert message.startswith("Refund of $5.00 processed successfully")


def test_verify_payment_status_invalid():
    gateway = PaymentGateway()
    result = gateway.verify_payment_status("invalid")
    assert result["status"] == "not_found"


def test_verify_payment_status_completed(frozen_time):
    gateway = PaymentGateway()
    result = gateway.verify_payment_status("txn_123")
    assert result["status"] == "completed"
    assert result["transaction_id"] == "txn_123"
