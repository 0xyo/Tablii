"""Restaurant, subscription, and operating hours models."""
from datetime import datetime, time as _time, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None

from app import db

DEFAULT_RAMADAN_IFTAR_TIME = _time(18, 30)
DEFAULT_RAMADAN_SUHOOR_END_TIME = _time(4, 30)


class Restaurant(db.Model):
    """A restaurant (tenant) on the platform."""

    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False
    )
    owner = db.relationship('User', back_populates='restaurants')
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(300), nullable=True)
    cover_url = db.Column(db.String(300), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    currency = db.Column(db.String(10), default='TND')
    tax_rate = db.Column(db.Float, default=0.0)
    service_charge = db.Column(db.Float, default=0.0)
    auto_accept = db.Column(db.Boolean, default=False)
    online_payment = db.Column(db.Boolean, default=False)
    default_language = db.Column(db.String(5), default='fr')
    ramadan_mode = db.Column(db.Boolean, default=False)
    ramadan_iftar_time = db.Column(
        db.Time,
        nullable=True,
        default=lambda: DEFAULT_RAMADAN_IFTAR_TIME,
    )
    loyalty_enabled = db.Column(db.Boolean, default=False)
    loyalty_points_per_unit = db.Column(db.Integer, default=10)  # points earned per currency unit spent
    loyalty_redemption_value = db.Column(db.Float, default=0.1)  # currency value per redeemed point
    is_active = db.Column(db.Boolean, default=True)
    is_open = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def is_currently_open(self):
        """Check if restaurant is open right now (manual override + schedule)."""
        if not self.is_open:
            return False
        from datetime import datetime, time as _time
        now = datetime.now()
        day = now.weekday()  # 0=Monday
        hours = OperatingHours.query.filter_by(
            restaurant_id=self.id, day_of_week=day
        ).first()
        if not hours:
            return True  # no schedule set = assume open
        if hours.is_closed:
            return False
        if hours.open_time and hours.close_time:
            current_time = now.time()
            if hours.open_time <= hours.close_time:
                return hours.open_time <= current_time <= hours.close_time
            else:
                # overnight (e.g. 20:00 - 02:00)
                return current_time >= hours.open_time or current_time <= hours.close_time
        return True

    def get_effective_ramadan_iftar_time(self):
        """Return the configured Iftar time or the platform fallback."""
        return self.ramadan_iftar_time or DEFAULT_RAMADAN_IFTAR_TIME

    def get_effective_ramadan_suhoor_end_time(self):
        """Return the configured Suhoor cutoff time or a safe fallback."""
        return DEFAULT_RAMADAN_SUHOOR_END_TIME

    def get_current_ramadan_service(self, now_time=None):
        """Return the active Ramadan service window for the given time."""
        if not self.ramadan_mode:
            return None
        if now_time is not None:
            current_time = now_time
        else:
            timezone_attr = getattr(self, 'timezone', None)
            tzinfo = timezone.utc
            if ZoneInfo and isinstance(timezone_attr, str) and timezone_attr.strip():
                try:
                    tzinfo = ZoneInfo(timezone_attr.strip())
                except Exception:
                    tzinfo = timezone.utc
            current_time = datetime.now(tzinfo).astimezone(tzinfo).time()

        if current_time >= self.get_effective_ramadan_iftar_time():
            return 'iftar'

        suhoor_end = self.get_effective_ramadan_suhoor_end_time()
        if current_time <= suhoor_end:
            return 'suhoor'

        return None

    # Relationships
    categories = db.relationship('Category', backref='restaurant', lazy='dynamic')
    tables = db.relationship('Table', backref='restaurant', lazy='dynamic')
    staff_users = db.relationship('StaffUser', backref='restaurant', lazy='dynamic')
    orders = db.relationship('Order', backref='restaurant', lazy='dynamic')
    subscription = db.relationship(
        'Subscription', back_populates='restaurant', uselist=False
    )
    operating_hours = db.relationship(
        'OperatingHours', backref='restaurant', lazy='dynamic'
    )


class Subscription(db.Model):
    """Subscription plan tied to a restaurant."""

    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'),
        unique=True, nullable=False
    )
    plan = db.Column(db.String(30), default='free')
    max_tables = db.Column(db.Integer, default=5)
    max_items = db.Column(db.Integer, default=20)
    started_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    restaurant = db.relationship('Restaurant', back_populates='subscription')


class OperatingHours(db.Model):
    """Weekly operating schedule for a restaurant."""

    __tablename__ = 'operating_hours'
    __table_args__ = (
        db.UniqueConstraint(
            'restaurant_id', 'day_of_week',
            name='uq_restaurant_day'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey('restaurants.id'), nullable=False
    )
    day_of_week = db.Column(db.Integer, nullable=False)
    open_time = db.Column(db.Time, nullable=True)
    close_time = db.Column(db.Time, nullable=True)
    is_closed = db.Column(db.Boolean, default=False)
