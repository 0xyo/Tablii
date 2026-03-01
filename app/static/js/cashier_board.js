/**
 * cashier_board.js — Live Kanban board logic for the cashier interface.
 */

const CSRF = document.querySelector('meta[name=csrf-token]')?.content || '';
let _newOrderSoundPlayed = false; // only play audio on WS events, not page load

function parseServerDate(value) {
    if (!value) return new Date();
    const normalized = String(value).replace(' ', 'T').trim();
    if (/[zZ]$|[+\-]\d{2}:\d{2}$/.test(normalized)) {
        return new Date(normalized);
    }
    return new Date(`${normalized}Z`);
}

function formatOrderNumber(value) {
    const raw = String(value || '').trim();
    if (!raw) return '#----';
    return raw.startsWith('#') ? raw : `#${raw}`;
}

// ---------------------------------------------------------------------------
// Timer helpers
// ---------------------------------------------------------------------------

/**
 * Start updating an order-timer element every second.
 * @param {HTMLElement} el  - Element with data-start ISO timestamp.
 */
function startCardTimer(el) {
    function update() {
        const start = parseServerDate(el.dataset.start);
        if (Number.isNaN(start.getTime())) return;
        const mins = Math.max(0, Math.floor((Date.now() - start.getTime()) / 60000));
        el.textContent = `${mins}m`;
        if (mins >= 20) {
            el.className = 'order-timer text-xs text-red-500 font-semibold';
        } else if (mins >= 10) {
            el.className = 'order-timer text-xs text-yellow-500 font-semibold';
        } else {
            el.className = 'order-timer text-xs text-gray-400';
        }
    }
    update();
    if (el._timerInterval) clearInterval(el._timerInterval);
    el._timerInterval = setInterval(update, 10000);
}

// ---------------------------------------------------------------------------
// Status update
// ---------------------------------------------------------------------------

/**
 * POST a status change; move card to new column on success.
 * @param {number} id
 * @param {string} status
 */
async function changeOrderStatus(id, status) {
    try {
        const res = await fetch(`/cashier/orders/${id}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF,
            },
            body: JSON.stringify({ new_status: status }),
        });
        const data = await res.json();

        if (!data.success) {
            alert(data.error || 'Could not update order.');
            return;
        }

        if (status === 'cancelled') {
            removeOrderCard(id);
        } else {
            moveOrderCard(id, status);
        }
    } catch (err) {
        console.error('changeOrderStatus error:', err);
    }
}

// ---------------------------------------------------------------------------
// DOM card manipulation
// ---------------------------------------------------------------------------

const NEXT_STATUS = {
    new: 'accepted',
    accepted: 'preparing',
    preparing: 'ready',
    ready: 'served',
};

const NEXT_LABEL = {
    accepted: 'Accept',
    preparing: 'Prepare',
    ready: 'Ready',
    served: 'Served',
};

/**
 * Animate the order card from its current column to newStatus column.
 * @param {number} id
 * @param {string} newStatus
 */
function moveOrderCard(id, newStatus) {
    const card = document.getElementById(`order-card-${id}`);
    if (!card) return;
    const oldStatus = card.dataset.status;

    // Fade out
    card.classList.add('moving');

    setTimeout(() => {
        const targetCol = document.getElementById(`cards-${newStatus}`);
        if (!targetCol) {
            // Status not shown (e.g. 'served') — just remove
            card.remove();
            updateColumnCount(oldStatus);
        } else {
            card.classList.remove('moving');
            card.dataset.status = newStatus;

            // Update action buttons
            const next = NEXT_STATUS[newStatus];
            const nextLabel = NEXT_LABEL[next] || next;
            const advanceBtn = card.querySelector('button:first-of-type');
            if (advanceBtn && next) {
                advanceBtn.textContent = `→ ${nextLabel}`;
                advanceBtn.setAttribute('onclick', `changeOrderStatus(${id}, '${next}')`);
            } else if (advanceBtn) {
                advanceBtn.remove();
            }
            // Hide cancel button for statuses that don't allow it
            const cancelBtn = card.querySelector('button:last-of-type');
            if (cancelBtn && cancelBtn.textContent.trim() === 'Cancel') {
                if (!['new', 'accepted'].includes(newStatus)) {
                    cancelBtn.remove();
                }
            }

            targetCol.appendChild(card);
            updateColumnCount(oldStatus);
            updateColumnCount(newStatus);
        }
    }, 280);
}

/**
 * Remove an order card (cancelled).
 * @param {number} id
 */
function removeOrderCard(id) {
    const card = document.getElementById(`order-card-${id}`);
    if (card) {
        card.classList.add('moving');
        const status = card.dataset.status;
        setTimeout(() => {
            card.remove();
            updateColumnCount(status);
        }, 280);
    }
}

/**
 * Recount cards in a column and update the badge.
 * @param {string} status
 */
function updateColumnCount(status) {
    const col = document.getElementById(`cards-${status}`);
    const badge = document.getElementById(`count-${status}`);
    if (col && badge) {
        badge.textContent = col.querySelectorAll('.order-card').length;
    }
}

// ---------------------------------------------------------------------------
// Add a new card (called by WebSocket events in Phase 08)
// ---------------------------------------------------------------------------

/**
 * Build and insert a new order card into the correct column.
 * @param {Object} data - {id, order_number, table_id, total_amount, status, created_at, items, currency}
 */
function addOrderToBoard(data) {
    const col = document.getElementById(`cards-${data.status}`);
    if (!col) return;

    const next = NEXT_STATUS[data.status];
    const nextLabel = NEXT_LABEL[next] || next;

    const card = document.createElement('div');
    card.className = 'order-card bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex flex-col gap-2';
    card.id = `order-card-${data.id}`;
    card.dataset.orderId = data.id;
    card.dataset.status = data.status;
    card.dataset.created = data.created_at;

    const itemsHtml = (data.items || []).map(i =>
        `<div class="flex gap-1">
            <span class="font-medium">${i.quantity}×</span>
            <span>${i.name}</span>
            ${i.notes ? `<span class="text-gray-400 italic">(${i.notes})</span>` : ''}
         </div>`
    ).join('');

    card.innerHTML = `
        <div class="flex items-center justify-between">
            <span class="font-bold text-gray-800 font-mono text-sm">${formatOrderNumber(data.order_number)}</span>
            <span class="text-xs px-2 py-0.5 rounded-full font-medium bg-orange-100 text-orange-700">
                ${data.table_id ? 'T' + data.table_id : '—'}
            </span>
        </div>
        <div class="text-xs text-gray-600 space-y-0.5">${itemsHtml}</div>
        <div class="flex items-center justify-between pt-1 border-t border-gray-50">
            <span class="text-sm font-semibold">${Number(data.total_amount).toFixed(3)} ${data.currency || ''}</span>
            <span class="order-timer text-xs text-gray-400" data-start="${data.created_at}">…</span>
        </div>
        ${next ? `<button onclick="changeOrderStatus(${data.id}, '${next}')"
                class="w-full text-xs font-medium bg-orange-500 hover:bg-orange-600 text-white py-1.5 rounded-lg transition-colors">
                → ${nextLabel}</button>` : ''}
        ${['new', 'accepted'].includes(data.status) ? `<button onclick="changeOrderStatus(${data.id}, 'cancelled')"
                class="w-full text-xs border border-red-200 text-red-400 hover:bg-red-50 py-1 rounded-lg transition-colors">
                Cancel</button>` : ''}`;

    col.appendChild(card);
    startCardTimer(card.querySelector('.order-timer'));
    updateColumnCount(data.status);
    playNewOrderSound();
}

// ---------------------------------------------------------------------------
// Audio
// ---------------------------------------------------------------------------

/**
 * Play new-order notification sound (only during live events, not page load).
 */
function playNewOrderSound() {
    if (_newOrderSoundPlayed) return; // guard for page load
    const audio = new Audio('/static/sounds/new_order.mp3');
    audio.volume = 0.6;
    audio.play().catch(() => {}); // ignore autoplay block
}

// Mark that subsequent calls will play sound
window.addEventListener('load', () => { _newOrderSoundPlayed = true; });
