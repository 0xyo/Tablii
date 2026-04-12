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


class TestGiftAndLoyaltyFlows:
    def test_gift_order_flow_end_to_end(self, client, db, sample_restaurant):
        """Customer can place a gift order to another occupied table."""
        from app.models.menu import Category, MenuItem
        from app.models.order import Order
        from app.models.table import Table, TableSession

        source_table = Table(
            restaurant_id=sample_restaurant.id,
            table_number=1,
            capacity=4,
            status='occupied',
        )
        target_table = Table(
            restaurant_id=sample_restaurant.id,
            table_number=2,
            capacity=4,
            status='occupied',
        )
        db.session.add_all([source_table, target_table])
        db.session.flush()

        table_session = TableSession(
            table_id=source_table.id,
            restaurant_id=sample_restaurant.id,
            session_token='session-token-gift',
            is_active=True,
        )
        db.session.add(table_session)

        cat = Category(
            restaurant_id=sample_restaurant.id,
            name_fr='Drinks',
            is_active=True,
        )
        db.session.add(cat)
        db.session.flush()

        item = MenuItem(
            restaurant_id=sample_restaurant.id,
            category_id=cat.id,
            name_fr='Lemonade',
            price=12.0,
            is_available=True,
        )
        db.session.add(item)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['session_token'] = table_session.session_token

        occupied_res = client.get(
            f'/r/{sample_restaurant.slug}/table/{source_table.id}/occupied-tables'
        )
        assert occupied_res.status_code == 200
        occupied_data = occupied_res.get_json()
        assert any(t['id'] == target_table.id for t in occupied_data['tables'])

        payload = {
            'items': [
                {
                    'menu_item_id': item.id,
                    'quantity': 1,
                    'selected_options': [],
                    'notes': '',
                }
            ],
            'payment_method': 'cash',
            'special_notes': 'Gift order test',
            'is_gift': True,
            'gift_to_table': target_table.id,
            'gift_message': 'Enjoy!',
        }
        res = client.post(
            f'/r/{sample_restaurant.slug}/table/{source_table.id}/order',
            json=payload,
        )
        assert res.status_code == 200, res.get_json()
        data = res.get_json()
        assert data['success'] is True

        order = db.session.get(Order, data['order_id'])
        assert order is not None
        assert order.is_gift is True
        assert order.table_id == target_table.id
        assert order.gift_from_table == source_table.table_number
        assert order.gift_message == 'Enjoy!'

    def test_loyalty_points_earned_on_order(self, client, db, sample_restaurant):
        """Placing an order with a linked customer should earn loyalty points."""
        from app.models.menu import Category, MenuItem
        from app.models.review import Customer, LoyaltyPoints
        from app.models.table import Table, TableSession

        sample_restaurant.loyalty_enabled = True
        sample_restaurant.loyalty_points_per_unit = 5

        table = Table(
            restaurant_id=sample_restaurant.id,
            table_number=3,
            capacity=4,
            status='occupied',
        )
        db.session.add(table)
        db.session.flush()

        customer = Customer(phone='12345678', name='Loyal Customer')
        db.session.add(customer)
        db.session.flush()

        table_session = TableSession(
            table_id=table.id,
            restaurant_id=sample_restaurant.id,
            session_token='session-token-loyalty',
            is_active=True,
            customer_id=customer.id,
        )
        db.session.add(table_session)

        cat = Category(
            restaurant_id=sample_restaurant.id,
            name_fr='Main',
            is_active=True,
        )
        db.session.add(cat)
        db.session.flush()

        item = MenuItem(
            restaurant_id=sample_restaurant.id,
            category_id=cat.id,
            name_fr='Pasta',
            price=10.0,
            is_available=True,
        )
        db.session.add(item)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['session_token'] = table_session.session_token

        res = client.post(
            f'/r/{sample_restaurant.slug}/table/{table.id}/order',
            json={
                'items': [
                    {
                        'menu_item_id': item.id,
                        'quantity': 2,
                        'selected_options': [],
                        'notes': '',
                    }
                ],
                'payment_method': 'cash',
                'special_notes': '',
                'is_gift': False,
            },
        )
        assert res.status_code == 200, res.get_json()
        data = res.get_json()
        assert data['success'] is True

        lp = LoyaltyPoints.query.filter_by(
            customer_id=customer.id,
            restaurant_id=sample_restaurant.id,
        ).first()
        assert lp is not None, 'Expected loyalty points row to be created.'

        expected_points = int(data['total_amount']) * sample_restaurant.loyalty_points_per_unit
        assert lp.points == expected_points
        assert lp.total_earned == expected_points
