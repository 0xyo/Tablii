"""Menu models: categories, items, customizations, and options."""
from app import db


class Category(db.Model):
    """Menu category with multi-language support."""

    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        nullable=False, index=True
    )
    name_ar = db.Column(db.String(100), nullable=True)
    name_fr = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=True)
    icon = db.Column(db.String(10), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    available_from = db.Column(db.Time, nullable=True)
    available_until = db.Column(db.Time, nullable=True)
    ramadan_type = db.Column(db.String(20), nullable=True)

    # Relationships
    items = db.relationship('MenuItem', backref='category', lazy='dynamic')


class MenuItem(db.Model):
    """Individual dish or product on the menu."""

    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey('categories.id'),
        nullable=False, index=True
    )
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        nullable=False, index=True
    )
    name_ar = db.Column(db.String(150), nullable=True)
    name_fr = db.Column(db.String(150), nullable=False)
    name_en = db.Column(db.String(150), nullable=True)
    description_ar = db.Column(db.Text, nullable=True)
    description_fr = db.Column(db.Text, nullable=True)
    description_en = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300), nullable=True)
    is_available = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    prep_time = db.Column(db.Integer, nullable=True)
    calories = db.Column(db.Integer, nullable=True)
    allergens = db.Column(db.String(300), nullable=True)
    is_popular = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    customizations = db.relationship(
        'Customization', backref='menu_item', lazy='dynamic'
    )


class Customization(db.Model):
    """A group of options for a menu item (e.g. 'Size', 'Extras')."""

    __tablename__ = 'customizations'

    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(
        db.Integer, db.ForeignKey('menu_items.id'), nullable=False
    )
    group_name_ar = db.Column(db.String(100), nullable=True)
    group_name_fr = db.Column(db.String(100), nullable=False)
    group_name_en = db.Column(db.String(100), nullable=True)
    selection_type = db.Column(db.String(20), nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    max_selections = db.Column(db.Integer, nullable=True)

    # Relationships
    options = db.relationship(
        'CustomOption', backref='customization', lazy='dynamic'
    )


class CustomOption(db.Model):
    """A single selectable option within a customization group."""

    __tablename__ = 'custom_options'

    id = db.Column(db.Integer, primary_key=True)
    customization_id = db.Column(
        db.Integer, db.ForeignKey('customizations.id'), nullable=False
    )
    name_ar = db.Column(db.String(100), nullable=True)
    name_fr = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=True)
    extra_price = db.Column(db.Float, default=0.0)
    is_default = db.Column(db.Boolean, default=False)
