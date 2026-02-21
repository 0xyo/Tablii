"""Analytics and reporting service for restaurant owners.

All functions:
- Accept ``restaurant_id`` as the first parameter and filter exclusively by it.
- Return JSON-serializable plain Python objects (dict / list).
- Use SQLAlchemy aggregate functions (func.sum, func.count, func.extract) for efficiency.
"""
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func

from app import db
from app.models.menu import MenuItem
from app.models.order import Order, OrderItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Daily Snapshot
# ---------------------------------------------------------------------------

def get_daily_stats(restaurant_id: int, target_date: date) -> dict:
    """Return a summary snapshot for a single day.

    Args:
        restaurant_id: Restaurant to query.
        target_date:   The date to snapshot (``datetime.date``).

    Returns:
        dict with total_orders, total_revenue, average_order_value,
        tables_used, orders_by_status, payment_methods.
    """
    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    base_q = Order.query.filter(
        Order.restaurant_id == restaurant_id,
        Order.created_at >= day_start,
        Order.created_at < day_end,
    )

    total_orders = base_q.count()
    total_revenue = (
        db.session.query(func.sum(Order.total_amount))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= day_start,
            Order.created_at < day_end,
            Order.payment_status == 'paid',
        )
        .scalar() or 0.0
    )

    avg_value = round(total_revenue / total_orders, 3) if total_orders else 0.0

    tables_used = (
        db.session.query(func.count(func.distinct(Order.table_id)))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= day_start,
            Order.created_at < day_end,
            Order.table_id.isnot(None),
        )
        .scalar() or 0
    )

    # Orders by status
    status_rows = (
        db.session.query(Order.status, func.count(Order.id))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= day_start,
            Order.created_at < day_end,
        )
        .group_by(Order.status)
        .all()
    )
    orders_by_status = {row[0]: row[1] for row in status_rows}

    # Payment methods
    method_rows = (
        db.session.query(Order.payment_method, func.count(Order.id))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= day_start,
            Order.created_at < day_end,
            Order.payment_method.isnot(None),
        )
        .group_by(Order.payment_method)
        .all()
    )
    payment_methods = {row[0]: row[1] for row in method_rows}

    return {
        'total_orders': total_orders,
        'total_revenue': round(float(total_revenue), 3),
        'average_order_value': avg_value,
        'tables_used': tables_used,
        'orders_by_status': orders_by_status,
        'payment_methods': payment_methods,
    }


# ---------------------------------------------------------------------------
# 2. Revenue by Period
# ---------------------------------------------------------------------------

def get_revenue_by_period(restaurant_id: int, start_date: date, end_date: date) -> list:
    """Return daily revenue totals across a date range.

    Args:
        restaurant_id: Restaurant to query.
        start_date:    Inclusive start date.
        end_date:      Inclusive end date.

    Returns:
        List of ``{'date': 'YYYY-MM-DD', 'revenue': float, 'orders': int}``.
    """
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=timezone.utc) + timedelta(days=1)

    rows = (
        db.session.query(
            func.date(Order.created_at).label('day'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('orders'),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= start_dt,
            Order.created_at < end_dt,
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )

    return [
        {
            'date': str(row.day),
            'revenue': round(float(row.revenue or 0), 3),
            'orders': row.orders,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 3. Popular Items
# ---------------------------------------------------------------------------

def get_popular_items(restaurant_id: int, period_days: int = 30) -> list:
    """Return the top-10 best-selling menu items.

    Args:
        restaurant_id: Restaurant to query.
        period_days:   How many past days to analyse.

    Returns:
        List of ``{'name': str, 'quantity_sold': int, 'revenue': float}``.
    """
    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    rows = (
        db.session.query(
            MenuItem.name_fr.label('name'),
            func.sum(OrderItem.quantity).label('quantity_sold'),
            func.sum(OrderItem.total_price).label('revenue'),
        )
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= since,
        )
        .group_by(MenuItem.id, MenuItem.name_fr)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
        .all()
    )

    return [
        {
            'name': row.name,
            'quantity_sold': int(row.quantity_sold or 0),
            'revenue': round(float(row.revenue or 0), 3),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 4. Peak Hours
# ---------------------------------------------------------------------------

def get_peak_hours(restaurant_id: int, period_days: int = 30) -> list:
    """Return order count grouped by hour of day.

    Args:
        restaurant_id: Restaurant to query.
        period_days:   Past days to analyse.

    Returns:
        List of ``{'hour': int, 'count': int}`` for hours 0–23.
    """
    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    rows = (
        db.session.query(
            func.extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('count'),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= since,
        )
        .group_by(func.extract('hour', Order.created_at))
        .order_by(func.extract('hour', Order.created_at))
        .all()
    )

    # Fill gaps with zeros for all 24 hours
    count_by_hour = {int(row.hour): int(row.count) for row in rows}
    return [{'hour': h, 'count': count_by_hour.get(h, 0)} for h in range(24)]


# ---------------------------------------------------------------------------
# 5. Average Service Time
# ---------------------------------------------------------------------------

def get_average_service_time(restaurant_id: int, period_days: int = 7) -> dict:
    """Return average durations at each stage of Order fulfilment.

    Only orders with all required timestamps are included in each metric.

    Args:
        restaurant_id: Restaurant to query.
        period_days:   Past days to analyse.

    Returns:
        dict with avg_accept_time, avg_prep_time, avg_total_time (all in seconds).
    """
    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    orders = (
        Order.query
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= since,
        )
        .all()
    )

    accept_times, prep_times, total_times = [], [], []

    for o in orders:
        if o.accepted_at and o.created_at:
            accept_times.append((o.accepted_at - o.created_at).total_seconds())
        if o.ready_at and o.accepted_at:
            prep_times.append((o.ready_at - o.accepted_at).total_seconds())
        if o.served_at and o.created_at:
            total_times.append((o.served_at - o.created_at).total_seconds())

    def _avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    return {
        'avg_accept_time': _avg(accept_times),
        'avg_prep_time': _avg(prep_times),
        'avg_total_time': _avg(total_times),
    }
