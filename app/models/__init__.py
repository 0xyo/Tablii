"""Import all models so Alembic migrations can detect them."""
from app.models.user import User, StaffUser  # noqa: F401
from app.models.restaurant import Restaurant, Subscription, OperatingHours  # noqa: F401
from app.models.menu import Category, MenuItem, Customization, CustomOption  # noqa: F401
from app.models.table import Table, TableSession  # noqa: F401
from app.models.order import Order, OrderItem, PaymentTransaction, WaiterCall  # noqa: F401
from app.models.review import Customer, Review, LoyaltyPoints, Notification  # noqa: F401
