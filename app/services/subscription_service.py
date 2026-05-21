"""Subscription and manager-location helpers."""
from datetime import time

from flask import session

from app import db
from app.models.restaurant import OperatingHours, Restaurant, Subscription

UNLIMITED_LIMIT = 999

PLAN_LIMITS = {
    'free': {
        'max_locations': 1,
        'max_tables': 5,
        'max_items': 20,
        'price': 0,
    },
    'pro': {
        'max_locations': 3,
        'max_tables': 25,
        'max_items': 100,
        'price': 49,
    },
    'enterprise': {
        'max_locations': UNLIMITED_LIMIT,
        'max_tables': UNLIMITED_LIMIT,
        'max_items': UNLIMITED_LIMIT,
        'price': 129,
    },
}
PLAN_ORDER = ('free', 'pro', 'enterprise')


def normalize_plan(plan):
    """Return a known plan key, defaulting unknown values to free."""
    return plan if plan in PLAN_LIMITS else 'free'


def get_plan_limits(plan):
    """Return limits for a subscription plan."""
    return PLAN_LIMITS[normalize_plan(plan)]


def apply_plan_limits(subscription, plan):
    """Apply the configured limit bundle for a plan to a subscription."""
    plan_key = normalize_plan(plan)
    limits = PLAN_LIMITS[plan_key]
    subscription.plan = plan_key
    subscription.max_locations = limits['max_locations']
    subscription.max_tables = limits['max_tables']
    subscription.max_items = limits['max_items']
    return subscription


def get_owner_subscription(owner):
    """Return the canonical subscription for an owner user."""
    owner_id = getattr(owner, 'id', None)
    if not owner_id:
        return None

    sub = Subscription.query.filter_by(owner_id=owner_id).first()
    if sub:
        return sub

    # Legacy fallback: older rows were attached to a restaurant only.
    return (
        Subscription.query
        .join(Restaurant, Subscription.restaurant_id == Restaurant.id)
        .filter(Restaurant.owner_id == owner_id)
        .order_by(Subscription.id)
        .first()
    )


def ensure_owner_subscription(owner, restaurant=None, plan='free', payment_completed=False):
    """Return an owner-level subscription, creating or upgrading legacy data."""
    owner_id = getattr(owner, 'id', None)
    if not owner_id:
        return None

    sub = get_owner_subscription(owner)
    if sub:
        sub.owner_id = owner_id
        if restaurant and not sub.restaurant_id:
            sub.restaurant_id = restaurant.id
        if not sub.max_locations or sub.max_locations < 1:
            sub.max_locations = get_plan_limits(sub.plan)['max_locations']
        return sub

    if restaurant is None:
        restaurant = (
            Restaurant.query
            .filter_by(owner_id=owner_id)
            .order_by(Restaurant.id)
            .first()
        )

    sub = Subscription(
        owner_id=owner_id,
        restaurant_id=restaurant.id if restaurant else None,
        plan=normalize_plan(plan),
        payment_completed=payment_completed,
    )
    apply_plan_limits(sub, sub.plan)
    db.session.add(sub)
    return sub


def active_locations_for_owner(owner):
    """Return active locations owned by a manager."""
    owner_id = getattr(owner, 'id', None)
    if not owner_id:
        return []
    return (
        Restaurant.query
        .filter_by(owner_id=owner_id, is_active=True)
        .order_by(Restaurant.id)
        .all()
    )


def active_location_count(owner):
    """Count active locations for an owner."""
    owner_id = getattr(owner, 'id', None)
    if not owner_id:
        return 0
    return Restaurant.query.filter_by(owner_id=owner_id, is_active=True).count()


def can_create_location(owner, subscription=None):
    """Return whether the owner can add another active location."""
    subscription = subscription or get_owner_subscription(owner)
    max_locations = subscription.max_locations if subscription else PLAN_LIMITS['free']['max_locations']
    return active_location_count(owner) < max_locations


def resolve_active_restaurant(owner):
    """Resolve the manager's selected active location from the session."""
    locations = active_locations_for_owner(owner)
    if not locations:
        session.pop('active_restaurant_id', None)
        return None

    selected_id = session.get('active_restaurant_id')
    try:
        selected_id = int(selected_id)
    except (TypeError, ValueError):
        selected_id = None

    for location in locations:
        if location.id == selected_id:
            return location

    session['active_restaurant_id'] = locations[0].id
    return locations[0]


def generate_unique_restaurant_slug(name):
    """Generate a unique restaurant slug."""
    from app.utils.helpers import generate_slug

    for _ in range(10):
        slug = generate_slug(name)
        if not Restaurant.query.filter_by(slug=slug).first():
            return slug
    base = generate_slug(name)
    suffix = Restaurant.query.count() + 1
    return f'{base}-{suffix}'


def create_default_operating_hours(restaurant):
    """Create the default weekly service hours for a new location."""
    for day in range(7):
        db.session.add(OperatingHours(
            restaurant_id=restaurant.id,
            day_of_week=day,
            open_time=time(9, 0),
            close_time=time(23, 0),
            is_closed=False,
        ))
