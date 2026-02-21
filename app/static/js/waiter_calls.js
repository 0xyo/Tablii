/**
 * waiter_calls.js
 * Client-side helpers for waiter call requests (customer side)
 * and incoming call display (waiter side).
 */

'use strict';

// ── Utility: simple toast ──────────────────────────────────────────────────

function _showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = [
    'fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-xl shadow-lg',
    'text-sm font-medium z-50 transition-opacity duration-500',
    type === 'success'
      ? 'bg-green-600 text-white'
      : 'bg-red-600 text-white',
  ].join(' ');
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 500);
  }, 3000);
}

// ── 1. callWaiter ──────────────────────────────────────────────────────────

/**
 * Send a waiter call request from the customer page.
 *
 * @param {string} slug     - Restaurant slug.
 * @param {number} tableId  - Table ID.
 * @param {string} type     - Call type: 'water' | 'bill' | 'help' | 'custom'.
 * @param {string} message  - Optional custom message.
 */
async function callWaiter(slug, tableId, type, message = '') {
  const url = `/r/${slug}/table/${tableId}/call-waiter`;
  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ call_type: type, message }),
    });
    const data = await res.json();
    if (data.success) {
      _showToast('Waiter has been called ✓');
    } else {
      _showToast(data.error || 'Failed to call waiter', 'error');
    }
  } catch (err) {
    console.error('callWaiter error:', err);
    _showToast('Network error — please try again.', 'error');
  }
}

// ── 2. showWaiterCall ──────────────────────────────────────────────────────

const CALL_TYPE_ICONS = {
  water:  '💧',
  bill:   '💳',
  help:   '🆘',
  custom: '📝',
};

/**
 * Display an incoming waiter call as a banner (waiter-side).
 *
 * @param {Object} data - { call_id, table_number, call_type, message }
 */
function showWaiterCall(data) {
  // Remove any existing banner for same call
  const existing = document.getElementById(`wc-${data.call_id}`);
  if (existing) existing.remove();

  const icon = CALL_TYPE_ICONS[data.call_type] || '🔔';

  const banner = document.createElement('div');
  banner.id = `wc-${data.call_id}`;
  banner.className = [
    'fixed top-4 right-4 z-50 max-w-xs w-full',
    'bg-orange-500 text-white rounded-xl shadow-2xl p-4',
    'flex items-start gap-3 animate-bounce',
  ].join(' ');
  banner.innerHTML = `
    <span class="text-2xl">${icon}</span>
    <div class="flex-1 min-w-0">
      <p class="font-bold text-sm">Table ${data.table_number}</p>
      <p class="text-xs capitalize">${data.call_type}${data.message ? ' — ' + data.message : ''}</p>
    </div>
    <button onclick="resolveCall(${data.call_id})"
            class="text-white/70 hover:text-white text-xs shrink-0">✕</button>
  `;
  document.body.appendChild(banner);
  banner.style.animation = 'none';

  // Haptic feedback
  if ('vibrate' in navigator) {
    navigator.vibrate([200, 100, 200]);
  }

  // Sound (if available via socket.js playSound)
  if (typeof playSound === 'function') {
    playSound('call_waiter');
  }

  // Auto-dismiss after 30 seconds
  setTimeout(() => banner.remove(), 30_000);
}

// ── 3. resolveCall ─────────────────────────────────────────────────────────

/**
 * Mark a waiter call as resolved.
 *
 * @param {number} callId
 */
async function resolveCall(callId) {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
  try {
    const res = await fetch(`/waiter/calls/${callId}/resolve`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
    });
    const data = await res.json();
    if (data.success) {
      const banner = document.getElementById(`wc-${callId}`);
      if (banner) banner.remove();
    }
  } catch (err) {
    console.error('resolveCall error:', err);
  }
}
