"""Tests for menu model creation and soft-delete behavior."""
import pytest


class TestCategory:
    def test_create_category(self, db, sample_restaurant):
        """Category must belong to its restaurant."""
        from app.models.menu import Category

        cat = Category(
            restaurant_id=sample_restaurant.id,
            name_fr='Entrées',
            is_active=True,
        )
        db.session.add(cat)
        db.session.commit()

        fetched = Category.query.get(cat.id)
        assert fetched is not None, 'Category should be persisted'
        assert fetched.restaurant_id == sample_restaurant.id, (
            'Category must belong to the sample restaurant'
        )
        assert fetched.name_fr == 'Entrées'


class TestMenuItem:
    def test_create_menu_item(self, db, sample_restaurant):
        """Menu item should be created with correct price and linked to restaurant."""
        from app.models.menu import Category, MenuItem

        cat = Category(restaurant_id=sample_restaurant.id, name_fr='Plats', is_active=True)
        db.session.add(cat)
        db.session.flush()

        item = MenuItem(
            restaurant_id=sample_restaurant.id,
            category_id=cat.id,
            name_fr='Tajine Poulet',
            price=16.5,
            is_available=True,
        )
        db.session.add(item)
        db.session.commit()

        fetched = MenuItem.query.get(item.id)
        assert fetched is not None, 'MenuItem should be persisted'
        assert fetched.price == pytest.approx(16.5), (
            f'Price should be 16.5, got {fetched.price}'
        )
        assert fetched.restaurant_id == sample_restaurant.id


class TestSoftDelete:
    def test_soft_delete_item(self, db, sample_restaurant):
        """Soft-deleted item must have deleted_at set and must be excluded from active queries."""
        from datetime import datetime, timezone
        from app.models.menu import Category, MenuItem

        cat = Category(restaurant_id=sample_restaurant.id, name_fr='Desserts', is_active=True)
        db.session.add(cat)
        db.session.flush()

        item = MenuItem(
            restaurant_id=sample_restaurant.id,
            category_id=cat.id,
            name_fr='Crème Brûlée',
            price=6.5,
            is_available=True,
        )
        db.session.add(item)
        db.session.commit()

        # Soft delete
        item.deleted_at = datetime.now(timezone.utc)
        db.session.commit()

        refetched = MenuItem.query.get(item.id)
        assert refetched.deleted_at is not None, 'deleted_at must be set after soft delete'

        # Active query must exclude deleted items
        active_items = (
            MenuItem.query
            .filter_by(restaurant_id=sample_restaurant.id)
            .filter(MenuItem.deleted_at.is_(None))
            .all()
        )
        item_ids = [i.id for i in active_items]
        assert item.id not in item_ids, 'Soft-deleted item must not appear in active queries'
