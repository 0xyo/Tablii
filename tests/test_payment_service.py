"""Mock tests for payment_service — Flouci gateway integration.

Uses unittest.mock to simulate external Flouci API calls without
making real HTTP requests. Validates initiation, verification,
and edge-case handling.
"""
from unittest.mock import patch, MagicMock


class TestInitiateFlouciPayment:
    """Tests for initiate_flouci_payment()."""

    def test_successful_initiation(self, app, db, order):
        """Mock Flouci API returns payment_url and payment_id."""
        from app.services.payment_service import initiate_flouci_payment

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'payment_id': 'PAY_123456',
            'link': 'https://flouci.com/pay/PAY_123456',
        }

        with patch('app.services.payment_service.requests.post', return_value=mock_response):
            result = initiate_flouci_payment(
                order_id=order.id,
                amount=25.0,
                success_url='http://localhost/success',
                fail_url='http://localhost/fail',
            )

        assert result is not None
        assert result['payment_url'] == 'https://flouci.com/pay/PAY_123456'
        assert result['payment_id'] == 'PAY_123456'

        # Verify PaymentTransaction was created
        from app.models.order import PaymentTransaction
        txn = PaymentTransaction.query.filter_by(order_id=order.id).first()
        assert txn is not None
        assert txn.gateway == 'flouci'
        assert txn.amount == 25.0
        assert txn.status == 'pending'

    def test_rejects_non_pending_order(self, app, db, order):
        """Should return None if order.payment_status != 'pending'."""
        from app.services.payment_service import initiate_flouci_payment

        order.payment_status = 'paid'
        db.session.commit()

        result = initiate_flouci_payment(
            order_id=order.id, amount=25.0,
            success_url='http://x', fail_url='http://y',
        )
        assert result is None

    def test_rejects_nonexistent_order(self, app, db):
        """Should return None for an order ID that doesn't exist."""
        from app.services.payment_service import initiate_flouci_payment

        result = initiate_flouci_payment(
            order_id=99999, amount=10.0,
            success_url='http://x', fail_url='http://y',
        )
        assert result is None

    def test_handles_api_error(self, app, db, order):
        """Should return None when Flouci API fails."""
        import requests as req
        from app.services.payment_service import initiate_flouci_payment

        with patch('app.services.payment_service.requests.post',
                   side_effect=req.RequestException('Timeout')):
            result = initiate_flouci_payment(
                order_id=order.id, amount=25.0,
                success_url='http://x', fail_url='http://y',
            )
        assert result is None

    def test_amount_converted_to_millimes(self, app, db, order):
        """Verify amount is multiplied by 1000 in the API payload."""
        from app.services.payment_service import initiate_flouci_payment

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'payment_id': 'PAY_789',
            'link': 'https://flouci.com/pay/PAY_789',
        }

        with patch('app.services.payment_service.requests.post',
                   return_value=mock_response) as mock_post:
            initiate_flouci_payment(
                order_id=order.id, amount=12.500,
                success_url='http://x', fail_url='http://y',
            )

        call_args = mock_post.call_args
        payload = call_args.kwargs.get('json') or call_args[1].get('json')
        assert payload['amount'] == 12500  # millimes


class TestVerifyFlouciPayment:
    """Tests for verify_flouci_payment()."""

    def test_successful_verification(self, app, db, order):
        """Mock successful Flouci verification updates order to 'paid'."""
        from app.services.payment_service import verify_flouci_payment
        from app.models.order import PaymentTransaction

        # Create a pending transaction first
        txn = PaymentTransaction(
            order_id=order.id, gateway='flouci', amount=25.0,
            gateway_transaction_id='PAY_VERIFY_OK', status='pending',
        )
        db.session.add(txn)
        db.session.commit()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'result': {'status': 'SUCCESS'},
        }

        with patch('app.services.payment_service.requests.get',
                   return_value=mock_response):
            result = verify_flouci_payment('PAY_VERIFY_OK')

        assert result is True

        # Verify database was updated
        db.session.refresh(txn)
        db.session.refresh(order)
        assert txn.status == 'completed'
        assert order.payment_status == 'paid'

    def test_failed_verification(self, app, db, order):
        """Mock failed Flouci verification returns False."""
        from app.services.payment_service import verify_flouci_payment
        from app.models.order import PaymentTransaction

        txn = PaymentTransaction(
            order_id=order.id, gateway='flouci', amount=25.0,
            gateway_transaction_id='PAY_VERIFY_FAIL', status='pending',
        )
        db.session.add(txn)
        db.session.commit()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'result': {'status': 'FAILURE'},
        }

        with patch('app.services.payment_service.requests.get',
                   return_value=mock_response):
            result = verify_flouci_payment('PAY_VERIFY_FAIL')

        assert result is False
        db.session.refresh(txn)
        assert txn.status == 'failed'

    def test_unknown_payment_id(self, app, db):
        """Should return False if no transaction found for payment_id."""
        from app.services.payment_service import verify_flouci_payment

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {'result': {'status': 'SUCCESS'}}

        with patch('app.services.payment_service.requests.get',
                   return_value=mock_response):
            result = verify_flouci_payment('UNKNOWN_ID')

        assert result is False

    def test_empty_payment_id(self, app, db):
        """Should return False for empty payment_id."""
        from app.services.payment_service import verify_flouci_payment
        assert verify_flouci_payment('') is False
        assert verify_flouci_payment(None) is False
