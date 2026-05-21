/**
 * cashier_board.js - Live Kanban board logic for the cashier interface.
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
        el.className = 'order-timer font-mono text-xs';
        if (mins >= 20) {
            el.style.color = 'var(--staff-accent)';
            el.style.fontWeight = '800';
        } else if (mins >= 10) {
            el.style.color = '#c7945b';
            el.style.fontWeight = '800';
        } else {
            el.style.color = 'var(--staff-muted)';
            el.style.fontWeight = '500';
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
    served: 'completed',
};

const NEXT_LABEL = {
    accepted: 'Accept',
    preparing: 'Prepare',
    ready: 'Ready',
    served: 'Served',
    completed: 'Complete',
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
            // Status not shown (e.g. 'served') - just remove
            card.remove();
            updateColumnCount(oldStatus);
        } else {
            card.classList.remove('moving');
            card.dataset.status = newStatus;

            // Update action buttons
            const next = NEXT_STATUS[newStatus];
            const nextLabel = NEXT_LABEL[next] || next;
            const advanceBtn = card.querySelector('[data-advance]');
            if (advanceBtn && next) {
                advanceBtn.textContent = nextLabel;
                advanceBtn.setAttribute('onclick', `changeOrderStatus(${id}, '${next}')`);
            } else if (advanceBtn) {
                advanceBtn.remove();
            }
            // Hide cancel button for statuses that don't allow it
            const cancelBtn = card.querySelector('[data-cancel]');
            if (cancelBtn && !['new', 'accepted'].includes(newStatus)) {
                cancelBtn.remove();
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

    const accent = 'var(--staff-accent)';
    const paymentStatus = data.payment_status || 'unpaid';
    const paymentMethod = data.payment_method || 'cash';

    const card = document.createElement('article');
    card.className = 'order-card staff-card p-4 flex flex-col gap-4';
    card.style.borderLeft = `3px solid ${accent}`;
    card.id = `order-card-${data.id}`;
    card.dataset.orderId = data.id;
    card.dataset.status = data.status;
    card.dataset.created = data.created_at;

    const itemsHtml = (data.items || []).map(i =>
        `<div class="flex gap-3 items-start text-sm leading-tight">
            <span class="font-mono font-bold shrink-0" style="color: ${accent};">${i.quantity}x</span>
            <div class="min-w-0">
                <p class="font-medium" style="color: var(--staff-dark);">${i.name}</p>
                ${i.notes ? `<p class="text-xs italic mt-1" style="color: var(--staff-muted);">Note: ${i.notes}</p>` : ''}
            </div>
         </div>`
    ).join('');

    card.innerHTML = `
        <div class="flex items-start justify-between gap-3">
            <div>
                <p class="font-mono text-sm font-bold" style="color: ${accent};">${formatOrderNumber(data.order_number)}</p>
                <p class="text-[9px] uppercase tracking-[0.14em] font-bold mt-1" style="color: var(--staff-muted);">Transaction</p>
            </div>
            <span class="staff-chip" style="background: rgba(245,237,231,0.84); color: var(--staff-dark);">
                ${data.table_id ? 'T-' + data.table_id : 'Takeaway'}
            </span>
        </div>
        <div class="flex flex-wrap gap-2">
            <span class="staff-chip" style="${paymentStatus === 'paid' ? 'background: rgba(197,212,200,0.18); color: var(--staff-green);' : 'background: rgba(184,95,59,0.1); color: var(--staff-accent);'}">
                ${paymentStatus === 'paid' ? 'Paid' : 'Unpaid'}
            </span>
            <span class="staff-chip" style="background: rgba(245,237,231,0.84); color: var(--staff-muted);">${paymentMethod}</span>
        </div>
        <div class="space-y-2 py-3" style="border-top: 1px solid var(--staff-border); border-bottom: 1px solid var(--staff-border);">${itemsHtml}</div>
        <div class="flex items-center justify-between gap-3">
            <span class="font-semibold" style="color: var(--staff-dark);">
                ${Number(data.total_amount).toFixed(3)}
                <span class="text-[9px] uppercase tracking-[0.12em] font-bold" style="color: var(--staff-muted);">${data.currency || ''}</span>
            </span>
            <span class="order-timer font-mono text-xs" style="color: var(--staff-muted);" data-start="${data.created_at}">00:00</span>
        </div>
        <div class="grid gap-2 mt-auto">
            ${paymentStatus !== 'paid' ? `<button type="button" onclick="confirmPayment(${data.id})" class="staff-action success w-full">Collect Payment</button>` : ''}
            <div class="flex gap-2">
                ${next ? `<button type="button" data-advance onclick="changeOrderStatus(${data.id}, '${next}')" class="staff-action primary flex-1">${nextLabel}</button>` : ''}
                ${['new', 'accepted'].includes(data.status) ? `<button type="button" data-cancel onclick="changeOrderStatus(${data.id}, 'cancelled')" class="staff-action danger w-12" title="Cancel Order" aria-label="Cancel order">X</button>` : ''}
            </div>
        </div>`;

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

// ---------------------------------------------------------------------------
// Confirm cash payment
// ---------------------------------------------------------------------------

async function confirmPayment(id) {
    try {
        const res = await fetch(`/cashier/orders/${id}/confirm-payment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF,
            },
        });
        const data = await res.json();
        if (data.success) {
            location.reload();
        } else {
            alert(data.error || 'Failed to confirm payment.');
        }
    } catch (err) {
        console.error('confirmPayment error:', err);
    }
}
