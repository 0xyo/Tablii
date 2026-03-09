"""Tests for JSON API endpoints."""
import json
import pytest


class TestMenuJson:
    def test_get_menu_json(self, client, db, sample_user, sample_restaurant):
        """GET /api/restaurant/<slug>/menu must return a valid JSON menu structure."""
        from app.models.menu import Category, MenuItem

        cat = Category(
            restaurant_id=sample_restaurant.id,
            name_fr='Entrées',
            icon='🥗',
            is_active=True,
            sort_order=1,
        )
        db.session.add(cat)
        db.session.flush()

        item = MenuItem(
            restaurant_id=sample_restaurant.id,
            category_id=cat.id,
            name_fr='Salade César',
            price=8.5,
            is_available=True,
        )
        db.session.add(item)
        db.session.commit()

        response = client.get(f'/api/restaurant/{sample_restaurant.slug}/menu')

        assert response.status_code == 200, (
            f'Expected 200, got {response.status_code}'
        )
        assert response.content_type.startswith('application/json'), (
            'Response must be JSON'
        )

        data = response.get_json()
        assert 'restaurant' in data, 'Response must contain "restaurant" key'
        assert 'categories' in data, 'Response must contain "categories" key'
        assert data['restaurant']['slug'] == sample_restaurant.slug, (
            'Restaurant slug must match'
        )
        assert isinstance(data['categories'], list), '"categories" must be a list'

        # Verify structure of the first category
        category_data = data['categories'][0]
        assert 'id' in category_data and 'name' in category_data, (
            'Category must have id and name'
        )
        assert 'items' in category_data and isinstance(category_data['items'], list), (
            'Category must have an items list'
        )

    def test_get_menu_json_not_found(self, client, db):
        """GET for unknown slug must return 404 JSON error."""
        response = client.get('/api/restaurant/nonexistent-slug/menu')
        assert response.status_code == 404, (
            f'Expected 404 for unknown slug, got {response.status_code}'
        )
        data = response.get_json()
        assert 'error' in data, 'JSON 404 response must contain "error" key'


class TestOrderStatusApi:
    def test_get_order_status(self, client, db, restaurant, order):
        """GET /api/order/<id>/status must return correct status and timestamps."""
        response = client.get(f'/api/order/{order.id}/status')

        assert response.status_code == 200, (
            f'Expected 200, got {response.status_code}'
        )
        assert response.content_type.startswith('application/json'), (
            'Response must be JSON'
        )

        data = response.get_json()
        assert data['order_id'] == order.id, 'order_id must match'
        assert data['status'] == order.status, 'status must match the order status'
        assert 'timestamps' in data, 'Response must contain "timestamps" key'

        timestamps = data['timestamps']
        required_keys = ['created_at', 'accepted_at', 'preparing_at', 'ready_at', 'served_at', 'completed_at']
        for key in required_keys:
            assert key in timestamps, f'Timestamp "{key}" must be present in response'

    def test_get_order_status_not_found(self, client, db):
        """GET for nonexistent order must return 404 JSON."""
        response = client.get('/api/order/999999/status')
        assert response.status_code == 404, (
            f'Expected 404 for unknown order, got {response.status_code}'
        )
        data = response.get_json()
        assert 'error' in data, 'JSON 404 response must contain "error" key'
