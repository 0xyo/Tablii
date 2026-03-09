"""Mock tests for notification_service — in-app notifications.

Tests CRUD operations on notification records using an in-memory
SQLite database.
"""


class TestCreateNotification:
    """Tests for create_notification()."""

    def test_creates_notification(self, app, db, restaurant):
        """Should create and return a Notification record."""
        from app.services.notification_service import create_notification

        notif = create_notification(
            restaurant_id=restaurant.id,
            type='order',
            title='New order received',
            body='Order #001 from Table 1',
        )

        assert notif.id is not None
        assert notif.restaurant_id == restaurant.id
        assert notif.type == 'order'
        assert notif.title == 'New order received'
        assert notif.is_read is False

    def test_with_target_role(self, app, db, restaurant):
        """Should set target_role correctly."""
        from app.services.notification_service import create_notification

        notif = create_notification(
            restaurant_id=restaurant.id,
            type='system',
            title='Kitchen alert',
            target_role='kitchen',
        )
        assert notif.target_role == 'kitchen'

    def test_with_target_user(self, app, db, restaurant):
        """Should set target_user_id correctly."""
        from app.services.notification_service import create_notification

        notif = create_notification(
            restaurant_id=restaurant.id,
            type='assignment',
            title='Table assigned',
            target_user_id=42,
        )
        assert notif.target_user_id == 42


class TestGetUnreadNotifications:
    """Tests for get_unread_notifications()."""

    def test_returns_unread_only(self, app, db, restaurant):
        """Should only return unread notifications."""
        from app.services.notification_service import (
            create_notification, get_unread_notifications,
        )

        n1 = create_notification(restaurant.id, 'order', 'Unread 1')
        n2 = create_notification(restaurant.id, 'order', 'Unread 2')

        # Mark one as read manually
        n1.is_read = True
        db.session.commit()

        result = get_unread_notifications(restaurant.id)
        assert len(result) == 1
        assert result[0].id == n2.id

    def test_filter_by_role(self, app, db, restaurant):
        """Should return notifications for a role + global ones."""
        from app.services.notification_service import (
            create_notification, get_unread_notifications,
        )

        create_notification(restaurant.id, 'order', 'For kitchen', target_role='kitchen')
        create_notification(restaurant.id, 'order', 'For waiter', target_role='waiter')
        create_notification(restaurant.id, 'system', 'For everyone')  # no target_role

        result = get_unread_notifications(restaurant.id, role='kitchen')
        titles = [n.title for n in result]
        assert 'For kitchen' in titles
        assert 'For everyone' in titles
        assert 'For waiter' not in titles

    def test_empty_restaurant(self, app, db, restaurant):
        """Should return empty list when no notifications exist."""
        from app.services.notification_service import get_unread_notifications

        result = get_unread_notifications(restaurant.id)
        assert result == []


class TestMarkNotificationRead:
    """Tests for mark_notification_read()."""

    def test_marks_as_read(self, app, db, restaurant):
        """Should set is_read=True and return True."""
        from app.services.notification_service import (
            create_notification, mark_notification_read,
        )

        notif = create_notification(restaurant.id, 'order', 'Test')
        result = mark_notification_read(notif.id, restaurant.id)

        assert result is True
        db.session.refresh(notif)
        assert notif.is_read is True

    def test_wrong_restaurant(self, app, db, restaurant):
        """Should return False for mismatched restaurant_id."""
        from app.services.notification_service import (
            create_notification, mark_notification_read,
        )

        notif = create_notification(restaurant.id, 'order', 'Test')
        result = mark_notification_read(notif.id, restaurant_id=99999)

        assert result is False
        db.session.refresh(notif)
        assert notif.is_read is False

    def test_nonexistent_id(self, app, db, restaurant):
        """Should return False for a notification that doesn't exist."""
        from app.services.notification_service import mark_notification_read

        result = mark_notification_read(99999, restaurant.id)
        assert result is False


class TestMarkAllRead:
    """Tests for mark_all_read()."""

    def test_marks_all(self, app, db, restaurant):
        """Should mark all unread notifications and return count."""
        from app.services.notification_service import (
            create_notification, mark_all_read, get_unread_notifications,
        )

        create_notification(restaurant.id, 'order', 'N1')
        create_notification(restaurant.id, 'order', 'N2')
        create_notification(restaurant.id, 'order', 'N3')

        count = mark_all_read(restaurant.id)
        assert count == 3

        remaining = get_unread_notifications(restaurant.id)
        assert remaining == []

    def test_marks_by_role(self, app, db, restaurant):
        """Should only mark notifications for the specified role."""
        from app.services.notification_service import (
            create_notification, mark_all_read, get_unread_notifications,
        )

        create_notification(restaurant.id, 'order', 'Kitchen1', target_role='kitchen')
        create_notification(restaurant.id, 'order', 'Waiter1', target_role='waiter')

        count = mark_all_read(restaurant.id, role='kitchen')
        assert count == 1

        remaining = get_unread_notifications(restaurant.id)
        assert len(remaining) == 1
        assert remaining[0].title == 'Waiter1'
