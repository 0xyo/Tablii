"""In-app notification management service."""
import logging

from app import db
from app.models.review import Notification

logger = logging.getLogger(__name__)


def create_notification(
    restaurant_id: int,
    type: str,
    title: str,
    body: str = None,
    target_role: str = None,
    target_user_id: int = None,
) -> Notification:
    """Create and persist a Notification record.

    Args:
        restaurant_id:  Restaurant the notification belongs to.
        type:           Category string (e.g. ``'order'``, ``'system'``).
        title:          Short headline.
        body:           Optional longer description.
        target_role:    If set, only staff with this role see it.
        target_user_id: If set, only this specific user sees it.

    Returns:
        The committed Notification instance.
    """
    notif = Notification(
        restaurant_id=restaurant_id,
        type=type,
        title=title,
        body=body,
        target_role=target_role,
        target_user_id=target_user_id,
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def get_unread_notifications(
    restaurant_id: int,
    role: str = None,
    user_id: int = None,
) -> list:
    """Return unread notifications for a restaurant, optionally filtered.

    Args:
        restaurant_id: Restaurant to query.
        role:          Optional role filter (``target_role``).
        user_id:       Optional user filter (``target_user_id``).

    Returns:
        List of Notification model instances, newest first.
    """
    q = Notification.query.filter_by(
        restaurant_id=restaurant_id,
        is_read=False,
    )
    if role is not None:
        q = q.filter(
            (Notification.target_role == role) | (Notification.target_role.is_(None))
        )
    if user_id is not None:
        q = q.filter(
            (Notification.target_user_id == user_id) | (Notification.target_user_id.is_(None))
        )
    return q.order_by(Notification.created_at.desc()).all()


def mark_notification_read(notification_id: int, restaurant_id: int) -> bool:
    """Mark a single notification as read.

    Args:
        notification_id: ID of the notification.
        restaurant_id:   Owner restriction (prevents cross-restaurant access).

    Returns:
        True on success, False if not found.
    """
    notif = Notification.query.filter_by(
        id=notification_id, restaurant_id=restaurant_id
    ).first()
    if notif is None:
        return False
    notif.is_read = True
    db.session.commit()
    return True


def mark_all_read(restaurant_id: int, role: str = None) -> int:
    """Mark all unread notifications as read, optionally for a specific role.

    Args:
        restaurant_id: Restaurant scope.
        role:          Optional role filter.

    Returns:
        Number of notifications updated.
    """
    q = Notification.query.filter_by(restaurant_id=restaurant_id, is_read=False)
    if role is not None:
        q = q.filter(Notification.target_role == role)
    count = q.count()
    q.update({'is_read': True}, synchronize_session=False)
    db.session.commit()
    return count
