"""
seed.py — Seed the database with rich Tunisian restaurant demo data.

Usage:
    venv\\Scripts\\python.exe seed.py

Creates (idempotent — safe to run multiple times):
    Super Admin : superadmin@tablii.com / admin1234
    Owner       : owner@tablii.com      / owner1234
    Restaurant  : Chez Ahmed (chez-ahmed)
    Staff       : 3 staff members (cashier, waiter, kitchen)
    Categories  : 4 (Entrées, Plats, Desserts, Boissons)
    Items       : 15 menu items with French/Arabic names
    Tables      : 8 tables
"""
from datetime import time, timedelta, datetime, timezone

from app import create_app, db
from app.models.menu import Category, MenuItem
from app.models.restaurant import OperatingHours, Restaurant, Subscription
from app.models.table import Table
from app.models.user import StaffUser, User
from app.utils.helpers import generate_slug


def seed():
    """Seed the database with demo data. Idempotent — skips existing records."""
    app = create_app('development')
    with app.app_context():
        db.create_all()

        # ── Super Admin ──────────────────────────────────────────────────────
        if not User.query.filter_by(email='superadmin@tablii.com').first():
            sa = User(
                name='Super Admin',
                email='superadmin@tablii.com',
                role='super_admin',
                is_active=True,
            )
            sa.set_password('admin1234')
            db.session.add(sa)
            db.session.flush()
            print('  [+] Super admin created')
        else:
            print('  [-] Super admin already exists, skipped')

        # ── Owner ────────────────────────────────────────────────────────────
        owner = User.query.filter_by(email='owner@tablii.com').first()
        if not owner:
            owner = User(
                name='Ahmed Ben Ali',
                email='owner@tablii.com',
                role='owner',
                is_active=True,
            )
            owner.set_password('owner1234')
            db.session.add(owner)
            db.session.flush()
            print('  [+] Owner created')
        else:
            print('  [-] Owner already exists, skipped')

        # ── Restaurant ───────────────────────────────────────────────────────
        restaurant = Restaurant.query.filter_by(slug='chez-ahmed').first()
        if not restaurant:
            restaurant = Restaurant(
                owner_id=owner.id,
                name='Chez Ahmed',
                slug='chez-ahmed',
                description='Cuisine tunisienne authentique -- saveurs du terroir',
                city='Tunis',
                address='15 Rue de la Kasbah, Tunis',
                phone='+21671000001',
                currency='TND',
                tax_rate=7.0,
                auto_accept=False,
                is_active=True,
                is_open=True,
            )
            db.session.add(restaurant)
            db.session.flush()
            print('  [+] Restaurant created')
        else:
            print('  [-] Restaurant already exists, skipped')

        # ── Subscription ─────────────────────────────────────────────────────
        if not restaurant.subscription:
            sub = Subscription(
                restaurant_id=restaurant.id,
                plan='pro',
                max_tables=20,
                max_items=100,
                is_active=True,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
            db.session.add(sub)
            print('  [+] Subscription (pro) created')

        # ── Operating Hours ──────────────────────────────────────────────────
        existing_hours = restaurant.operating_hours.count()
        if existing_hours == 0:
            for day in range(7):
                db.session.add(OperatingHours(
                    restaurant_id=restaurant.id,
                    day_of_week=day,
                    open_time=time(10, 0),
                    close_time=time(23, 0),
                    is_closed=False,
                ))
            print('  [+] Operating hours created (10:00-23:00 daily)')

        # ── Staff ────────────────────────────────────────────────────────────
        staff_data = [
            {'username': 'caisse1',   'name': 'Sami Caissier',  'role': 'cashier',  'password': 'staff1234'},
            {'username': 'serveur1',  'name': 'Rim Serveuse',   'role': 'waiter',   'password': 'staff1234'},
            {'username': 'cuisine1',  'name': 'Omar Cuisine',   'role': 'kitchen',  'password': 'staff1234'},
        ]
        for s in staff_data:
            exists = StaffUser.query.filter_by(
                restaurant_id=restaurant.id, username=s['username']
            ).first()
            if not exists:
                staff = StaffUser(
                    restaurant_id=restaurant.id,
                    username=s['username'],
                    name=s['name'],
                    role=s['role'],
                    is_active=True,
                )
                staff.set_password(s['password'])
                db.session.add(staff)
        db.session.flush()
        print('  [+] Staff created (cashier, waiter, kitchen)')

        # ── Categories ───────────────────────────────────────────────────────
        existing_cats = restaurant.categories.count()
        cats = {}
        if existing_cats == 0:
            categories_data = [
                {'name_fr': 'Entrees',   'name_ar': None, 'name_en': 'Starters', 'icon': None, 'sort_order': 1},
                {'name_fr': 'Plats',     'name_ar': None, 'name_en': 'Mains',    'icon': None, 'sort_order': 2},
                {'name_fr': 'Desserts',  'name_ar': None, 'name_en': 'Desserts', 'icon': None, 'sort_order': 3},
                {'name_fr': 'Boissons',  'name_ar': None, 'name_en': 'Drinks',   'icon': None, 'sort_order': 4},
            ]
            for c in categories_data:
                cat = Category(
                    restaurant_id=restaurant.id,
                    name_fr=c['name_fr'],
                    name_ar=c['name_ar'],
                    name_en=c['name_en'],
                    icon=c['icon'],
                    sort_order=c['sort_order'],
                    is_active=True,
                )
                db.session.add(cat)
                db.session.flush()
                cats[c['name_fr']] = cat
            print('  [+] 4 categories created')
        else:
            for cat in restaurant.categories.all():
                cats[cat.name_fr] = cat
            print('  [-] Categories already exist, skipped')

        # ── Menu Items ───────────────────────────────────────────────────────
        existing_items = MenuItem.query.filter_by(restaurant_id=restaurant.id).count()
        if existing_items == 0 and cats:
            items_data = [
                # Entrees
                {'name_fr': 'Salade Mechouia',         'price': 7.500,  'cat': 'Entrees',  'is_popular': True},
                {'name_fr': "Brik a l'oeuf",           'price': 5.000,  'cat': 'Entrees'},
                {'name_fr': 'Chorba Frik',              'price': 6.000,  'cat': 'Entrees'},
                {'name_fr': 'Salade Tunisienne',        'price': 5.500,  'cat': 'Entrees'},
                # Plats
                {'name_fr': 'Couscous Agneau',          'price': 22.000, 'cat': 'Plats',    'is_popular': True},
                {'name_fr': 'Tajine Poulet Olives',     'price': 18.500, 'cat': 'Plats'},
                {'name_fr': 'Merguez Grillees',         'price': 16.000, 'cat': 'Plats'},
                {'name_fr': 'Makloub de la Mer',        'price': 24.000, 'cat': 'Plats',    'is_popular': True},
                {'name_fr': 'Lablabi',                  'price': 9.000,  'cat': 'Plats'},
                {'name_fr': 'Kafteji',                  'price': 11.000, 'cat': 'Plats'},
                # Desserts
                {'name_fr': 'Baklawa Maison',           'price': 8.000,  'cat': 'Desserts'},
                {'name_fr': 'Creme Caramel',            'price': 6.000,  'cat': 'Desserts'},
                {'name_fr': 'Assida Zgougou',           'price': 7.500,  'cat': 'Desserts', 'is_popular': True},
                # Boissons
                {'name_fr': 'Jus de Grenade Frais',    'price': 5.500,  'cat': 'Boissons'},
                {'name_fr': 'Eau Minerale',             'price': 1.500,  'cat': 'Boissons'},
            ]
            for i in items_data:
                db.session.add(MenuItem(
                    restaurant_id=restaurant.id,
                    category_id=cats[i['cat']].id,
                    name_fr=i['name_fr'],
                    price=i['price'],
                    is_available=True,
                    is_popular=i.get('is_popular', False),
                ))
            print('  [+] 15 menu items created')
        else:
            print('  [-] Menu items already exist, skipped')

        # ── Tables ───────────────────────────────────────────────────────────
        existing_tables = restaurant.tables.count()
        if existing_tables == 0:
            for n in range(1, 9):
                db.session.add(Table(
                    restaurant_id=restaurant.id,
                    table_number=n,
                    capacity=4,
                    status='free',
                ))
            print('  [+] 8 tables created')
        else:
            print('  [-] Tables already exist, skipped')

        db.session.commit()

        print()
        print('[OK] Seed complete!')
        print()
        print('  Super Admin : superadmin@tablii.com / admin1234')
        print('  Owner Login : owner@tablii.com / owner1234')
        print('  Restaurant  : Chez Ahmed (slug: chez-ahmed)')
        print('  Staff       : caisse1 / serveur1 / cuisine1 (password: staff1234)')
        print()
        print('  Menu API    : http://127.0.0.1:5000/api/restaurant/chez-ahmed/menu')
        print('  Login URL   : http://127.0.0.1:5000/login')
        print('  Admin URL   : http://127.0.0.1:5000/admin/restaurants')


if __name__ == '__main__':
    seed()
