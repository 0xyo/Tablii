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

        sub = Subscription.query.filter_by(owner_id=sample_user.id).first()
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

        locations_response = client.get('/dashboard/locations')
        assert locations_response.status_code == 403

        post_response = client.post(
            '/dashboard/subscription/change',
            data={'plan': 'free'},
        )
        assert post_response.status_code == 403

    def test_free_plan_blocks_second_location(
        self, client, db, sample_user, sample_restaurant
    ):
        """Free owner subscriptions should allow only one active location."""
        from app.models.restaurant import Restaurant, Subscription

        db.session.add(Subscription(
            owner_id=sample_user.id,
            restaurant_id=sample_restaurant.id,
            plan='free',
            max_locations=1,
            max_tables=5,
            max_items=20,
            payment_completed=True,
        ))
        db.session.commit()

        login_response = _login_owner(client, sample_user)
        assert login_response.status_code == 302

        response = client.post(
            '/dashboard/locations/add',
            data={'name': 'Second Branch'},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'Location limit reached' in response.data
        assert Restaurant.query.filter_by(
            owner_id=sample_user.id,
            is_active=True,
        ).count() == 1

    def test_pro_plan_can_create_and_switch_location_scope(
        self, client, db, sample_user, sample_restaurant
    ):
        """Switching active locations should change dashboard data scope."""
        from app.models.restaurant import Restaurant, Subscription
        from app.models.table import Table

        db.session.add(Subscription(
            owner_id=sample_user.id,
            restaurant_id=sample_restaurant.id,
            plan='pro',
            max_locations=3,
            max_tables=25,
            max_items=100,
            payment_completed=True,
        ))
        db.session.add(Table(
            restaurant_id=sample_restaurant.id,
            table_number=1,
            capacity=4,
        ))
        db.session.commit()

        login_response = _login_owner(client, sample_user)
        assert login_response.status_code == 302

        response = client.post(
            '/dashboard/locations/add',
            data={'name': 'Branch Two'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Branch Two created and selected' in response.data

        branch_two = Restaurant.query.filter_by(
            owner_id=sample_user.id,
            name='Branch Two',
        ).first()
        assert branch_two is not None
        db.session.add(Table(
            restaurant_id=branch_two.id,
            table_number=9,
            capacity=2,
        ))
        db.session.commit()

        response = client.get('/dashboard/tables')
        assert response.status_code == 200
        assert b'>T9<' in response.data
        assert b'>T1<' not in response.data

        response = client.post(
            f'/dashboard/locations/{sample_restaurant.id}/switch',
            data={'next': '/dashboard/tables'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'>T1<' in response.data
        assert b'>T9<' not in response.data

        response = client.post(
            '/dashboard/locations/add',
            data={'name': 'Branch Three'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Branch Three created and selected' in response.data

        response = client.post(
            '/dashboard/locations/add',
            data={'name': 'Branch Four'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b'Location limit reached' in response.data
        assert Restaurant.query.filter_by(
            owner_id=sample_user.id,
            is_active=True,
        ).count() == 3


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
        assert restaurant.get_current_ramadan_service(time(3, 0)) == 'suhoor'
        assert restaurant.get_current_ramadan_service(time(17, 0)) is None
        assert restaurant.get_current_ramadan_service(time(19, 0)) == 'iftar'

    @pytest.mark.parametrize(
        ('current_time', 'expected_texts', 'missing_texts', 'service_text'),
        [
            (time(3, 0), [b'Suhoor Choices'], [b'Iftar Specials'], b'Affichage du menu Suhoor.'),
            (time(17, 0), [b'Iftar Specials', b'Suhoor Choices'], [], None),
            (time(19, 0), [b'Iftar Specials'], [b'Suhoor Choices'], b'Affichage du menu Iftar.'),
        ],
    )
    def test_customer_menu_filters_ramadan_categories_by_time(
        self,
        client,
        db,
        sample_restaurant,
        monkeypatch,
        current_time,
        expected_texts,
        missing_texts,
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
        for expected_text in expected_texts:
            assert expected_text in response.data
        for missing_text in missing_texts:
            assert missing_text not in response.data
        if service_text:
            assert service_text in response.data
        else:
            assert b'Mode Ramadan' not in response.data
