"""Shared pytest fixtures for Tablii tests."""
import os
import pytest

# Force testing config before any Flask import
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key'

from app import create_app, db as _db  # noqa: E402


@pytest.fixture(scope='session')
def app():
    """Create application for the test session using TestingConfig."""
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'WTF_CSRF_ENABLED': False,
        'FLOUCI_APP_TOKEN': 'test-token',
        'FLOUCI_APP_SECRET': 'test-secret',
    })
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    """Provide a clean database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_user(db):
    """Create a sample owner user."""
    from app.models.user import User
    user = User(email='test@test.com', name='Test Owner', role='owner')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_restaurant(db, sample_user):
    """Create a sample restaurant linked to sample_user."""
    from app.models.restaurant import Restaurant
    r = Restaurant(
        owner_id=sample_user.id,
        name='Test Resto',
        slug='test-resto',
    )
    db.session.add(r)
    db.session.commit()
    return r


@pytest.fixture
def restaurant(db):
    """Create a test restaurant (standalone, owner_id=1)."""
    from app.models.restaurant import Restaurant
    r = Restaurant(
        name='Test Restaurant',
        slug='test-restaurant',
        owner_id=1,
        is_active=True,
    )
    db.session.add(r)
    db.session.commit()
    return r


@pytest.fixture
def table(db, restaurant):
    """Create a test table."""
    from app.models.table import Table
    t = Table(
        restaurant_id=restaurant.id,
        table_number=1,
        capacity=4,
    )
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def order(db, restaurant, table):
    """Create a test order."""
    from app.models.order import Order
    o = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        order_number='ORD001',
        status='new',
        payment_method='cash',
        payment_status='pending',
        subtotal=25.0,
        total_amount=25.0,
    )
    db.session.add(o)
    db.session.commit()
    return o
