"""Mock tests for analytics_service — reporting and statistics.

Tests run against an in-memory SQLite database with seeded orders
to verify correct aggregation, filtering, and edge-case handling.
"""
from datetime import datetime, timedelta, timezone


class TestGetDailyStats:
    """Tests for get_daily_stats()."""

    def test_empty_restaurant(self, app, db, restaurant):
        """Should return zeros when no orders exist."""
        from app.services.analytics_service import get_daily_stats
        from datetime import date

        stats = get_daily_stats(restaurant.id, date.today())

        assert stats['total_orders'] == 0
        assert stats['total_revenue'] == 0.0
        assert stats['average_order_value'] == 0.0
        assert stats['tables_used'] == 0
        assert stats['orders_by_status'] == {}
        assert stats['payment_methods'] == {}

    def test_with_orders(self, app, db, restaurant, table):
        """Should calculate correct totals with seeded orders."""
        from app.services.analytics_service import get_daily_stats
        from app.models.order import Order
        from datetime import date

        # Seed 3 orders: 2 paid, 1 pending
        now = datetime.now(timezone.utc)
        o1 = Order(restaurant_id=restaurant.id, table_id=table.id,
                   order_number='A01', status='served', payment_method='cash',
                   payment_status='paid', total_amount=15.0, created_at=now)
        o2 = Order(restaurant_id=restaurant.id, table_id=table.id,
                   order_number='A02', status='completed', payment_method='online',
                   payment_status='paid', total_amount=30.500, created_at=now)
        o3 = Order(restaurant_id=restaurant.id, table_id=table.id,
                   order_number='A03', status='new', payment_method='cash',
                   payment_status='pending', total_amount=10.0, created_at=now)
        db.session.add_all([o1, o2, o3])
        db.session.commit()

        stats = get_daily_stats(restaurant.id, date.today())

        assert stats['total_orders'] == 3
        assert stats['total_revenue'] == 45.5  # 15.0 + 30.5 (only paid)
        assert stats['tables_used'] == 1
        assert 'cash' in stats['payment_methods']

    def test_filters_by_restaurant(self, app, db, restaurant, table):
        """Should not include orders from a different restaurant."""
        from app.services.analytics_service import get_daily_stats
        from app.models.order import Order
        from app.models.restaurant import Restaurant
        from datetime import date

        other = Restaurant(name='Other', slug='other', owner_id=2)
        db.session.add(other)
        db.session.flush()

        o = Order(restaurant_id=other.id, order_number='X01',
                  status='new', total_amount=100.0,
                  created_at=datetime.now(timezone.utc))
        db.session.add(o)
        db.session.commit()

        stats = get_daily_stats(restaurant.id, date.today())
        assert stats['total_orders'] == 0


class TestGetRevenueByPeriod:
    """Tests for get_revenue_by_period()."""

    def test_returns_daily_totals(self, app, db, restaurant, table):
        """Should return a list of daily revenue entries."""
        from app.services.analytics_service import get_revenue_by_period
        from app.models.order import Order
        from datetime import date

        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        o1 = Order(restaurant_id=restaurant.id, order_number='R01',
                   total_amount=20.0, created_at=now)
        o2 = Order(restaurant_id=restaurant.id, order_number='R02',
                   total_amount=15.0, created_at=yesterday)
        db.session.add_all([o1, o2])
        db.session.commit()

        result = get_revenue_by_period(
            restaurant.id,
            (date.today() - timedelta(days=1)),
            date.today(),
        )

        assert isinstance(result, list)
        assert len(result) >= 1  # at least one day with data
        for entry in result:
            assert 'date' in entry
            assert 'revenue' in entry
            assert 'orders' in entry

    def test_empty_period(self, app, db, restaurant):
        """Should return empty list for a period with no orders."""
        from app.services.analytics_service import get_revenue_by_period
        from datetime import date

        future = date.today() + timedelta(days=30)
        result = get_revenue_by_period(restaurant.id, future, future)
        assert result == []


class TestGetPopularItems:
    """Tests for get_popular_items()."""

    def test_returns_top_items(self, app, db, restaurant):
        """Should return a list of top items (may be empty with no orders)."""
        from app.services.analytics_service import get_popular_items

        result = get_popular_items(restaurant.id, period_days=30)
        assert isinstance(result, list)
        assert len(result) <= 10

    def test_respects_limit(self, app, db, restaurant, table):
        """Should never return more than 10 items."""
        from app.services.analytics_service import get_popular_items
        from app.models.menu import Category, MenuItem
        from app.models.order import Order, OrderItem

        cat = Category(restaurant_id=restaurant.id, name_fr='Cat', sort_order=1)
        db.session.add(cat)
        db.session.flush()

        # Create 15 items with orders
        now = datetime.now(timezone.utc)
        for i in range(15):
            item = MenuItem(restaurant_id=restaurant.id, category_id=cat.id,
                            name_fr=f'Item{i}', price=5.0)
            db.session.add(item)
            db.session.flush()

            order = Order(restaurant_id=restaurant.id, order_number=f'P{i:02d}',
                          total_amount=5.0, created_at=now)
            db.session.add(order)
            db.session.flush()

            oi = OrderItem(order_id=order.id, menu_item_id=item.id,
                           quantity=i + 1, unit_price=5.0, total_price=5.0 * (i + 1))
            db.session.add(oi)

        db.session.commit()

        result = get_popular_items(restaurant.id, period_days=30)
        assert len(result) == 10


class TestGetPeakHours:
    """Tests for get_peak_hours()."""

    def test_returns_24_hours(self, app, db, restaurant):
        """Should always return exactly 24 entries (one per hour)."""
        from app.services.analytics_service import get_peak_hours

        result = get_peak_hours(restaurant.id, period_days=30)
        assert len(result) == 24
        assert result[0]['hour'] == 0
        assert result[23]['hour'] == 23

    def test_all_zeros_when_empty(self, app, db, restaurant):
        """All counts should be 0 with no orders."""
        from app.services.analytics_service import get_peak_hours

        result = get_peak_hours(restaurant.id, period_days=30)
        assert all(h['count'] == 0 for h in result)


class TestGetAverageServiceTime:
    """Tests for get_average_service_time()."""

    def test_no_orders_returns_none(self, app, db, restaurant):
        """All averages should be None when no orders exist."""
        from app.services.analytics_service import get_average_service_time

        result = get_average_service_time(restaurant.id, period_days=7)
        assert result['avg_accept_time'] is None
        assert result['avg_prep_time'] is None
        assert result['avg_total_time'] is None

    def test_with_timed_orders(self, app, db, restaurant, table):
        """Should compute correct average times."""
        from app.services.analytics_service import get_average_service_time
        from app.models.order import Order

        now = datetime.now(timezone.utc)
        o = Order(
            restaurant_id=restaurant.id, table_id=table.id,
            order_number='T01', total_amount=10.0,
            created_at=now - timedelta(minutes=30),
            accepted_at=now - timedelta(minutes=25),   # 5 min accept
            ready_at=now - timedelta(minutes=10),       # 15 min prep
            served_at=now,                               # 30 min total
        )
        db.session.add(o)
        db.session.commit()

        result = get_average_service_time(restaurant.id, period_days=7)
        assert result['avg_accept_time'] == pytest.approx(300, abs=5)   # ~5 min
        assert result['avg_prep_time'] == pytest.approx(900, abs=5)     # ~15 min
        assert result['avg_total_time'] == pytest.approx(1800, abs=5)   # ~30 min


# Need pytest for approx
import pytest
