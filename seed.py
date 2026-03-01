"""
seed.py — Create a demo owner account + restaurant with sample data for testing.

Usage:
    venv\\Scripts\\python.exe seed.py

Creates:
    Owner email : admin@tablii.com
    Password    : admin1234
    Restaurant  : Demo Restaurant
"""
from datetime import time

from app import create_app, db
from app.models.menu import Category, MenuItem
from app.models.restaurant import OperatingHours, Restaurant, Subscription
from app.models.table import Table
from app.models.user import User
from app.utils.helpers import generate_slug
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Ensure all tables exist (safe to run even if already migrated)
    db.create_all()

    # Skip if already seeded
    if User.query.filter_by(email='admin@tablii.com').first():
        print('Seed already applied — admin@tablii.com already exists.')
    else:
        # 1. Create the owner user
        owner = User(
            name='Admin User',
            email='admin@tablii.com',
            password_hash=generate_password_hash('admin1234'),
            role='owner',
            is_active=True,
        )
        db.session.add(owner)
        db.session.flush()   # get owner.id

        # 2. Create the restaurant
        restaurant = Restaurant(
            name='Demo Restaurant',
            slug=generate_slug('Demo Restaurant'),
            owner_id=owner.id,
            currency='TND',
            is_active=True,
            is_open=True,
        )
        db.session.add(restaurant)
        db.session.flush()   # get restaurant.id

        # 3. Subscription (required for subscription checks)
        subscription = Subscription(restaurant_id=restaurant.id, plan='free')
        db.session.add(subscription)

        # 4. Default operating hours: Mon–Sun, 09:00–23:00
        for day in range(7):
            db.session.add(OperatingHours(
                restaurant_id=restaurant.id,
                day_of_week=day,
                open_time=time(9, 0),
                close_time=time(23, 0),
                is_closed=False,
            ))

        # 5. Sample menu categories
        categories_data = [
            {'name_fr': 'Entrées',      'name_en': 'Starters',  'icon': '🥗', 'sort_order': 1},
            {'name_fr': 'Plats',        'name_en': 'Main',      'icon': '🍽️', 'sort_order': 2},
            {'name_fr': 'Grillades',    'name_en': 'Grills',    'icon': '🥩', 'sort_order': 3},
            {'name_fr': 'Sandwichs',    'name_en': 'Sandwiches','icon': '🥪', 'sort_order': 4},
            {'name_fr': 'Pizzas',       'name_en': 'Pizzas',    'icon': '🍕', 'sort_order': 5},
            {'name_fr': 'Desserts',     'name_en': 'Desserts',  'icon': '🍰', 'sort_order': 6},
            {'name_fr': 'Boissons',     'name_en': 'Drinks',    'icon': '🥤', 'sort_order': 7},
        ]
        cats = {}
        for c in categories_data:
            cat = Category(
                restaurant_id=restaurant.id,
                name_fr=c['name_fr'],
                name_en=c['name_en'],
                icon=c['icon'],
                sort_order=c['sort_order'],
                is_active=True,
            )
            db.session.add(cat)
            db.session.flush()
            cats[c['name_fr']] = cat

        # 6. Sample menu items
        items_data = [
            {'name_fr': 'Salade César',      'price': 8.500,  'cat': 'Entrées'},
            {'name_fr': 'Soupe du jour',     'price': 5.000,  'cat': 'Entrées'},
            {'name_fr': 'Couscous Agneau',   'price': 18.000, 'cat': 'Plats'},
            {'name_fr': 'Tajine Poulet',     'price': 16.500, 'cat': 'Plats'},
            {'name_fr': 'Entrecôte',         'price': 22.000, 'cat': 'Grillades'},
            {'name_fr': 'Brochettes',        'price': 14.000, 'cat': 'Grillades'},
            {'name_fr': 'Sandwich Tunisien', 'price': 7.000,  'cat': 'Sandwichs'},
            {'name_fr': 'Pizza Margherita',  'price': 12.000, 'cat': 'Pizzas'},
            {'name_fr': 'Crème Brûlée',      'price': 6.500,  'cat': 'Desserts'},
            {'name_fr': 'Eau Minérale',      'price': 1.500,  'cat': 'Boissons'},
            {'name_fr': 'Jus d\'Orange',     'price': 4.000,  'cat': 'Boissons'},
        ]
        for i in items_data:
            db.session.add(MenuItem(
                restaurant_id=restaurant.id,
                category_id=cats[i['cat']].id,
                name_fr=i['name_fr'],
                price=i['price'],
                is_available=True,
            ))

        # 7. Sample tables
        for n in range(1, 9):
            db.session.add(Table(
                restaurant_id=restaurant.id,
                table_number=n,
                capacity=4,
                status='free',
            ))

        db.session.commit()

        print('Seed complete!')
        print()
        print('  Login URL : http://127.0.0.1:5000/login')
        print('  Email     : admin@tablii.com')
        print('  Password  : admin1234')
        print()
        print('  Created   : 7 categories, 11 menu items, 8 tables')
