"""Access-control decorators for role and restaurant enforcement."""
import functools

from flask import abort, g
from flask_login import current_user

from app.models.user import User, StaffUser


def role_required(*roles: str):
    """Restrict a route to specific user/staff roles.

    Super admins bypass role checks automatically.

    Args:
        *roles: Allowed role strings (e.g. 'cashier', 'owner').

    Usage::

        @role_required('cashier', 'owner')
        def cashier_dashboard():
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            if isinstance(current_user, User):
                if current_user.role == 'super_admin' or current_user.role in roles:
                    return f(*args, **kwargs)
            elif isinstance(current_user, StaffUser):
                if current_user.role in roles:
                    return f(*args, **kwargs)

            abort(403)
        return decorated_function
    return decorator


def restaurant_required(f):
    """Ensure the current user is associated with a restaurant.

    Loads the restaurant and stores it in ``g.restaurant``.
    Aborts with 404 if no restaurant is found.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)

        if isinstance(current_user, User):
            restaurant = current_user.restaurants.first()
            if restaurant is None:
                abort(404, description='No restaurant found')
        elif isinstance(current_user, StaffUser):
            restaurant = current_user.restaurant
        else:
            abort(403)

        g.restaurant = restaurant
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """Restrict a route to super admin users only."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if (
            not current_user.is_authenticated
            or not isinstance(current_user, User)
            or current_user.role != 'super_admin'
        ):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
