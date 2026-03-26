"""Loyalty points earning and redemption service."""
import logging

from app import db  # type: ignore[attr-defined]
from app.models.review import LoyaltyPoints

logger = logging.getLogger(__name__)


def earn_points(customer_id, restaurant, order_total):
    """Award loyalty points for a completed order.

    Points = floor(order_total) * restaurant.loyalty_points_per_unit.
    """
    if not restaurant.loyalty_enabled or not customer_id:
        return 0

    pts = int(order_total) * (restaurant.loyalty_points_per_unit or 10)
    if pts <= 0:
        return 0

    lp = LoyaltyPoints.query.filter_by(
        customer_id=customer_id, restaurant_id=restaurant.id
    ).first()
    if not lp:
        lp = LoyaltyPoints(
            customer_id=customer_id,
            restaurant_id=restaurant.id,
            points=0, total_earned=0, total_redeemed=0,
        )
        db.session.add(lp)

    lp.points += pts
    lp.total_earned += pts
    return pts


def redeem_points(customer_id, restaurant, points_to_redeem):
    """Redeem points for a discount. Returns discount amount or 0."""
    if not restaurant.loyalty_enabled or not customer_id or points_to_redeem <= 0:
        return 0.0

    lp = LoyaltyPoints.query.filter_by(
        customer_id=customer_id, restaurant_id=restaurant.id
    ).first()
    if not lp or lp.points < points_to_redeem:
        return 0.0

    discount = points_to_redeem * (restaurant.loyalty_redemption_value or 0.1)
    lp.points -= points_to_redeem
    lp.total_redeemed += points_to_redeem
    return round(discount, 3)


def get_balance(customer_id, restaurant_id):
    """Return current points balance for a customer at a restaurant."""
    if not customer_id:
        return 0
    lp = LoyaltyPoints.query.filter_by(
        customer_id=customer_id, restaurant_id=restaurant_id
    ).first()
    return lp.points if lp else 0
