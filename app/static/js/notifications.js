/**
 * notifications.js
 * Browser Notification API helpers.
 * Always check permission before creating notifications.
 */

'use strict';

// ── 1. requestNotificationPermission ──────────────────────────────────────

/**
 * Prompt the user for browser notification permission.
 * Only asks if permission is in the default (undecided) state.
 */
function requestNotificationPermission() {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {
      // Permission prompt suppressed or failed — silently ignore.
    });
  }
}

// ── 2. showDesktopNotification ─────────────────────────────────────────────

/**
 * Display a desktop notification if permission is granted.
 *
 * @param {string} title - Notification headline.
 * @param {string} body  - Notification body text.
 * @param {string} icon  - URL of the icon image.
 * @returns {Notification|null}
 */
function showDesktopNotification(
  title,
  body,
  icon = '/static/images/logo.png',
) {
  if (!('Notification' in window)) return null;
  if (Notification.permission !== 'granted') return null;

  return new Notification(title, { body, icon });
}

// ── 3. vibratePhone ───────────────────────────────────────────────────────

/**
 * Trigger haptic vibration on supported devices.
 *
 * @param {number|number[]} pattern - Vibration pattern in ms.
 */
function vibratePhone(pattern = [200]) {
  if ('vibrate' in navigator) {
    navigator.vibrate(pattern);
  }
}
