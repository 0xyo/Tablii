"""Tests for order creation, status machine, and order number formatting."""
import pytest


class TestCreateOrder:
    def test_create_order(self, db):
        """Order created via service should compute totals correctly."""
        from app.models.menu import Category, MenuItem
        from app.models.restaurant import Restaurant
        from app.services.order_service import create_order

        restaurant = Restaurant(name='Order Test', slug='order-test', owner_id=1, tax_rate=10.0)
        db.session.add(restaurant)
        db.session.flush()

        cat = Category(restaurant_id=restaurant.id, name_fr='Plats', is_active=True)
        db.session.add(cat)
        db.session.flush()

        item = MenuItem(
            restaurant_id=restaurant.id,
            category_id=cat.id,
            name_fr='Couscous',
            price=20.0,
            is_available=True,
        )
        db.session.add(item)
        db.session.commit()

        order = create_order(
            session_id=None,
            items=[{'menu_item_id': item.id, 'quantity': 2, 'selected_options': [], 'notes': ''}],
            payment_method='cash',
            special_notes=None,
            restaurant=restaurant,
        )

        assert order.subtotal == pytest.approx(40.0), (
            f'Subtotal should be 40.0, got {order.subtotal}'
        )
        assert order.tax_amount == pytest.approx(4.0), (
            f'Tax amount (10%) should be 4.0, got {order.tax_amount}'
        )
        assert order.total_amount == pytest.approx(44.0), (
            f'Total should be 44.0, got {order.total_amount}'
        )


class TestOrderStatusTransitions:
    def test_order_status_transitions_valid(self, db, restaurant, order):
        """Valid status transitions should succeed."""
        from app.services.order_service import update_order_status

        success, msg = update_order_status(order.id, 'accepted', restaurant.id)
        assert success is True, f'Expected success, got: {msg}'

        success, msg = update_order_status(order.id, 'preparing', restaurant.id)
        assert success is True, f'Expected success for preparing transition, got: {msg}'

    def test_order_status_transitions_invalid(self, db, restaurant, order):
        """Invalid transitions should be rejected with a descriptive error."""
        from app.services.order_service import update_order_status

        # Cannot jump from 'new' to 'completed'
        success, msg = update_order_status(order.id, 'completed', restaurant.id)
        assert success is False, 'Transition from new → completed must fail'
        assert 'Cannot transition' in msg, f'Expected transition error message, got: {msg}'


class TestOrderNumber:
    def test_order_number_generated(self, db):
        """generate_order_number() should return a # followed by 4 uppercase alphanumeric chars."""
        from app.utils.helpers import generate_order_number

        number = generate_order_number()
        assert number.startswith('#'), f'Order number must start with #, got: {number}'
        assert len(number) == 5, f'Order number must be 5 chars (#XXXX), got: {number}'
        assert number[1:].isalnum(), f'Order number suffix must be alphanumeric, got: {number[1:]}'
