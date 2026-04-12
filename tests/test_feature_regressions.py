"""Regression tests for recent feature-audit fixes."""
from datetime import datetime as real_datetime, time

import pytest


def _login_owner(client, user):
    """Log in an owner user for dashboard route tests."""
    return client.post(
        '/login',
        data={
            'login_type': 'owner',
            'email': user.email,
            'password': 'password123',
        },
        follow_redirects=False,
    )


def _login_staff(client, restaurant_slug, username):
    """Log in a staff user for permission tests."""
    return client.post(
        '/login',
        data={
            'login_type': 'staff',
            'restaurant_slug': restaurant_slug,
            'username': username,
            'password': 'password123',
        },
        follow_redirects=False,
    )


class TestSubscriptionManagement:
    def test_owner_cannot_self_upgrade_to_paid_plan(
        self, client, db, sample_user, sample_restaurant
    ):
        """Owner upgrades to paid plans should be blocked until billing exists."""
        from app.models.restaurant import Subscription

        login_response = _login_owner(client, sample_user)
        assert login_response.status_code == 302

        response = client.post(
            '/dashboard/subscription/change',
            data={'plan': 'enterprise'},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'Paid upgrades are not self-serve yet' in response.data

        sub = Subscription.query.filter_by(
            restaurant_id=sample_restaurant.id
        ).first()
        assert sub is None or sub.plan == 'free'

    def test_staff_cannot_access_subscription_routes(
        self, client, db, sample_restaurant
    ):
        """Staff accounts should not be able to manage billing pages."""
        from app.models.user import StaffUser

        staff = StaffUser(
            restaurant_id=sample_restaurant.id,
            username='cashier1',
            name='Cashier One',
            role='cashier',
        )
        staff.set_password('password123')
        db.session.add(staff)
        db.session.commit()

        login_response = _login_staff(client, sample_restaurant.slug, staff.username)
        assert login_response.status_code == 302

        response = client.get('/dashboard/subscription')
        assert response.status_code == 403

        post_response = client.post(
            '/dashboard/subscription/change',
            data={'plan': 'free'},
        )
        assert post_response.status_code == 403


class TestRamadanMode:
    def test_restaurant_uses_default_ramadan_iftar_time_when_missing(self):
        """Restaurants without a saved Iftar time should fall back to 18:30."""
        from app.models.restaurant import DEFAULT_RAMADAN_IFTAR_TIME, Restaurant

        restaurant = Restaurant(
            owner_id=1,
            name='Fallback Cafe',
            slug='fallback-cafe',
            ramadan_mode=True,
            ramadan_iftar_time=None,
        )

        assert restaurant.get_effective_ramadan_iftar_time() == DEFAULT_RAMADAN_IFTAR_TIME
        assert restaurant.get_current_ramadan_service(time(17, 0)) == 'suhoor'
        assert restaurant.get_current_ramadan_service(time(19, 0)) == 'iftar'

    @pytest.mark.parametrize(
        ('current_time', 'expected_text', 'missing_text', 'service_text'),
        [
            (time(17, 0), b'Suhoor Choices', b'Iftar Specials', b'Showing the Suhoor menu.'),
            (time(19, 0), b'Iftar Specials', b'Suhoor Choices', b'Showing the Iftar menu.'),
        ],
    )
    def test_customer_menu_filters_ramadan_categories_by_time(
        self,
        client,
        db,
        sample_restaurant,
        monkeypatch,
        current_time,
        expected_text,
        missing_text,
        service_text,
    ):
        """Menu should only render the active Ramadan meal window."""
        import app.routes.customer as customer_routes
        from app.models.menu import Category, MenuItem
        from app.models.table import Table

        class FrozenDateTime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                return real_datetime(
                    2026,
                    3,
                    15,
                    current_time.hour,
                    current_time.minute,
                    0,
                    tzinfo=tz,
                )

        monkeypatch.setattr(customer_routes, 'datetime', FrozenDateTime)

        sample_restaurant.ramadan_mode = True
        sample_restaurant.ramadan_iftar_time = time(18, 30)
        db.session.add(sample_restaurant)
        db.session.flush()

        table = Table(
            restaurant_id=sample_restaurant.id,
            table_number=9,
            capacity=4,
        )
        db.session.add(table)
        db.session.flush()

        iftar_category = Category(
            restaurant_id=sample_restaurant.id,
            name_fr='Iftar Specials',
            ramadan_type='iftar',
            is_active=True,
        )
        suhoor_category = Category(
            restaurant_id=sample_restaurant.id,
            name_fr='Suhoor Choices',
            ramadan_type='suhoor',
            is_active=True,
        )
        db.session.add_all([iftar_category, suhoor_category])
        db.session.flush()

        db.session.add_all(
            [
                MenuItem(
                    restaurant_id=sample_restaurant.id,
                    category_id=iftar_category.id,
                    name_fr='Harira',
                    price=8.5,
                    is_available=True,
                ),
                MenuItem(
                    restaurant_id=sample_restaurant.id,
                    category_id=suhoor_category.id,
                    name_fr='Lablabi',
                    price=7.0,
                    is_available=True,
                ),
            ]
        )
        db.session.commit()

        response = client.get(
            f'/r/{sample_restaurant.slug}/table/{table.id}',
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert expected_text in response.data
        assert missing_text not in response.data
        assert service_text in response.data
