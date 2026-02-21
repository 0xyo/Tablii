"""Flouci payment gateway integration service.

Strict rules:
- App token & secret are read from Flask config — never from client input.
- Payment amounts are converted to millimes (×1000) as Flouci requires.
- Rate-limit: one active PaymentTransaction per order (unique constraint in DB).
- Secrets are never logged at any level.
"""
import json
import logging

import requests
from flask import current_app

from app import db
from app.models.order import Order, PaymentTransaction

logger = logging.getLogger(__name__)

FLOUCI_BASE = 'https://developers.flouci.com/api'
TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initiate_flouci_payment(order_id: int, amount: float, success_url: str, fail_url: str):
    """Initiate a Flouci online payment for an order.

    Args:
        order_id:    ID of the Order to pay.
        amount:      Amount in TND (e.g. 12.500).
        success_url: Redirect URL on payment success.
        fail_url:    Redirect URL on payment failure.

    Returns:
        dict with ``payment_url`` and ``payment_id``, or ``None`` on error.
    """
    order = Order.query.get(order_id)
    if order is None:
        logger.warning('initiate_flouci_payment: order %s not found', order_id)
        return None

    if order.payment_status != 'pending':
        logger.warning(
            'initiate_flouci_payment: order %s already has payment_status=%s',
            order_id, order.payment_status,
        )
        return None

    app_token = current_app.config.get('FLOUCI_APP_TOKEN', '')
    app_secret = current_app.config.get('FLOUCI_APP_SECRET', '')
    if not app_token or not app_secret:
        logger.error('Flouci credentials not configured')
        return None

    payload = {
        'app_token': app_token,
        'app_secret': app_secret,
        'amount': int(amount * 1000),   # Flouci uses millimes
        'accept_card': 'true',
        'session_timeout_secs': 1200,
        'success_link': success_url,
        'fail_link': fail_url,
        'developer_tracking_id': str(order_id),
    }

    try:
        resp = requests.post(
            f'{FLOUCI_BASE}/generate_payment',
            json=payload,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error('Flouci initiate request failed: %s', exc)
        return None
    except ValueError:
        logger.error('Flouci initiate: non-JSON response')
        return None

    payment_id = data.get('payment_id') or data.get('paymentId')
    payment_url = data.get('link') or data.get('payment_link')

    if not payment_id or not payment_url:
        logger.error('Flouci initiate: unexpected response shape %s', list(data.keys()))
        return None

    # Persist transaction record
    try:
        txn = PaymentTransaction(
            order_id=order_id,
            gateway='flouci',
            amount=amount,
            gateway_transaction_id=str(payment_id),
            status='pending',
        )
        db.session.add(txn)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Failed to persist PaymentTransaction for order %s', order_id)
        return None

    return {'payment_url': payment_url, 'payment_id': payment_id}


def verify_flouci_payment(payment_id: str) -> bool:
    """Verify a Flouci payment by its ID and update the order/transaction.

    Args:
        payment_id: The Flouci payment_id string.

    Returns:
        True if payment was successful and records updated; False otherwise.
    """
    if not payment_id:
        return False

    try:
        resp = requests.get(
            f'{FLOUCI_BASE}/verify_payment/{payment_id}',
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error('Flouci verify request failed: %s', exc)
        return False

    result = data.get('result', {})
    status = result.get('status', '')

    txn = PaymentTransaction.query.filter_by(
        gateway_transaction_id=str(payment_id)
    ).first()

    if txn is None:
        logger.warning('verify_flouci_payment: no Transaction found for payment_id=%s', payment_id)
        return False

    raw_json = json.dumps(data, ensure_ascii=False)

    try:
        if status == 'SUCCESS':
            txn.status = 'completed'
            txn.raw_response = raw_json
            order = Order.query.get(txn.order_id)
            if order:
                order.payment_status = 'paid'
            db.session.commit()
            return True
        else:
            txn.status = 'failed'
            txn.raw_response = raw_json
            db.session.commit()
            return False
    except Exception:
        db.session.rollback()
        logger.exception('Failed to update payment records for payment_id=%s', payment_id)
        return False
