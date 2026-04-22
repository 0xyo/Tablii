"""Tests for authentication routes (register, login, logout)."""
import pytest


class TestRegister:
    def test_register_success(self, client, db):
        """POST valid data should create user and redirect to dashboard."""
        response = client.post('/register', data={
            'name': 'New Owner',
            'email': 'newowner@example.com',
            'phone': '12345678',
            'password': 'securepass1',
            'confirm_password': 'securepass1',
            'restaurant_name': 'New Place',
        }, follow_redirects=False)

        assert response.status_code == 302, (
            f'Expected redirect (302), got {response.status_code}'
        )

        from app.models.user import User
        user = User.query.filter_by(email='newowner@example.com').first()
        assert user is not None, 'User should exist in database after successful registration'
        assert user.name == 'New Owner'
        assert user.role == 'owner'

    def test_register_duplicate_email(self, client, db, sample_user):
        """POST with an existing email should not create a duplicate user."""
        response = client.post('/register', data={
            'name': 'Duplicate',
            'email': sample_user.email,
            'password': 'password123',
            'confirm_password': 'password123',
            'restaurant_name': 'Duplicate Place',
        }, follow_redirects=True)

        assert response.status_code == 200, (
            'Should stay on register page when email is duplicate'
        )
        # Only one user with this email should exist
        from app.models.user import User
        count = User.query.filter_by(email=sample_user.email).count()
        assert count == 1, 'Duplicate user must not be created'


class TestLogin:
    def test_login_valid_owner(self, client, db, sample_user, sample_restaurant):
        """Valid credentials should redirect to dashboard."""
        response = client.post('/login', data={
            'login_type': 'owner',
            'email': sample_user.email,
            'password': 'password123',
        }, follow_redirects=False)

        assert response.status_code == 302, (
            f'Expected redirect (302) after successful login, got {response.status_code}'
        )
        assert '/dashboard' in response.headers.get('Location', ''), (
            'Successful login should redirect to /dashboard'
        )

    def test_login_invalid_password(self, client, db, sample_user):
        """Wrong password should not log in the user."""
        response = client.post('/login', data={
            'login_type': 'owner',
            'email': sample_user.email,
            'password': 'wrongpassword',
        }, follow_redirects=False)

        assert response.status_code == 302, 'Should redirect back to login'
        location = response.headers.get('Location', '')
        assert '/dashboard' not in location, (
            'Invalid credentials must not redirect to dashboard'
        )

    def test_logout(self, client, db, sample_user, sample_restaurant):
        """Logging out should clear session and redirect to login."""
        # Log in first
        client.post('/login', data={
            'login_type': 'owner',
            'email': sample_user.email,
            'password': 'password123',
        })

        response = client.get('/logout', follow_redirects=False)
        assert response.status_code == 302, 'Logout should redirect'

        location = response.headers.get('Location', '')
        assert 'login' in location, 'After logout, should redirect to login page'


def test_owner_bootstrap_is_available_when_demo_bootstrap_requested(monkeypatch):
    """Startup should ensure the demo owner account exists on hosted bootstraps."""
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    monkeypatch.setenv('SOCKETIO_CORS_ORIGINS', '*')
    monkeypatch.setenv('TABLII_SUPERADMIN_EMAIL', 'superadmin@tablii.com')
    monkeypatch.setenv('TABLII_SUPERADMIN_PASSWORD', 'admin1234')
    monkeypatch.delenv('TABLII_OWNER_EMAIL', raising=False)
    monkeypatch.delenv('TABLII_OWNER_PASSWORD', raising=False)
    monkeypatch.delenv('TABLII_AUTO_SEED', raising=False)

    from app import create_app, db, _ensure_owner_from_env
    from app.models.restaurant import Restaurant
    from app.models.user import User

    app = create_app('development')
    with app.app_context():
        db.create_all()
        _ensure_owner_from_env(app)
        owner = User.query.filter_by(email='owner@tablii.com').first()
        assert owner is not None
        assert owner.role == 'owner'
        assert owner.check_password('owner1234')
        restaurant = Restaurant.query.filter_by(owner_id=owner.id).first()
        assert restaurant is not None
        assert restaurant.slug == 'chez-ahmed'
        db.drop_all()
