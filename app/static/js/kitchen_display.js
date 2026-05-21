/**
 * kitchen_display.js - Timer logic and status updates for the kitchen screen.
 */

const CSRF = document.querySelector('meta[name=csrf-token]')?.content || '';

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
// Timers
// ---------------------------------------------------------------------------

/**
 * Start a live timer on a kitchen-timer element.
 * Colors: normal to yellow after 10 min to red after 20 min.
 * @param {HTMLElement} el - Element with data-start ISO timestamp.
 */
function startTimer(el) {
    function update() {
        const start = parseServerDate(el.dataset.start);
        if (Number.isNaN(start.getTime())) return;
        const totalSecs = Math.max(0, Math.floor((Date.now() - start.getTime()) / 1000));
        const mins = Math.floor(totalSecs / 60);
        const secs = totalSecs % 60;
        el.textContent = `${mins}:${String(secs).padStart(2, '0')}`;

        el.className = 'kitchen-timer font-mono text-sm ';
        if (mins >= 20) {
            el.className += 'timer-urgent';
        } else if (mins >= 10) {
            el.className += 'timer-warn';
        } else {
            el.className += 'timer-normal';
        }
    }
    update();
    if (el._timerInterval) clearInterval(el._timerInterval);
    el._timerInterval = setInterval(update, 1000);
}

// ---------------------------------------------------------------------------
// Status actions
// ---------------------------------------------------------------------------

/**
 * Move an order to 'preparing' - card moves from queue to cooking.
 * @param {number} id
 */
async function markAsPreparing(id) {
    const ok = await _postStatus(id, 'preparing');
    if (ok) {
        _moveKitchenCard(id, 'accepted', 'preparing');
    }
}

/**
 * Mark an order as 'ready' - card removed from kitchen display.
 * @param {number} id
 */
async function markAsReady(id) {
    const ok = await _postStatus(id, 'ready');
    if (ok) {
        _removeKitchenCard(id);
    }
}

async function _postStatus(id, status) {
    try {
        const res = await fetch(`/kitchen/orders/${id}/${status}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF,
            },
        });
        const data = await res.json();
        if (!data.success) {
            console.warn('Kitchen status error:', data.error);
            return false;
        }
        return true;
    } catch (err) {
        console.error('Kitchen fetch error:', err);
        return false;
    }
}

function _removeKitchenCard(id) {
    const card = document.getElementById(`kcard-${id}`);
    if (!card) return;
    card.classList.add('removing');
    setTimeout(() => {
        card.remove();
        _updateCount('preparing');
    }, 300);
}

function _moveKitchenCard(id, fromStatus, toStatus) {
    const card = document.getElementById(`kcard-${id}`);
    if (!card) return;

    card.classList.add('removing');
    setTimeout(() => {
        card.classList.remove('removing');
        card.style.borderLeft = '3px solid var(--staff-gold)';
        const orderNumber = card.querySelector('.font-mono');
        if (orderNumber) orderNumber.style.color = 'var(--staff-gold)';
        const stateLabel = card.querySelector('p.text-\\[10px\\]');
        if (stateLabel) stateLabel.textContent = 'Cooking';
        const qtyLabels = card.querySelectorAll('li .font-mono');
        qtyLabels.forEach(label => { label.style.color = 'var(--staff-gold)'; });
        // Update button to "Ready"
        const btn = card.querySelector('button');
        if (btn) {
            btn.textContent = 'Ready to Serve';
            btn.className = 'staff-action gold';
            btn.setAttribute('onclick', `markAsReady(${id})`);
        }
        // Update timer to now
        const timerEl = card.querySelector('.kitchen-timer');
        if (timerEl) {
            timerEl.dataset.start = new Date().toISOString();
            startTimer(timerEl);
        }

        const targetCol = document.getElementById('col-preparing');
        if (targetCol) targetCol.appendChild(card);

        _updateCount(fromStatus);
        _updateCount(toStatus);
    }, 300);
}

function _updateCount(status) {
    const col = document.getElementById(`col-${status}`);
    const badge = document.getElementById(`count-${status}`);
    if (col && badge) badge.textContent = col.querySelectorAll('.kitchen-card').length;
}

// ---------------------------------------------------------------------------
// Add new card (called from WebSocket in Phase 08)
// ---------------------------------------------------------------------------

/**
 * Add a new order card to the kitchen accepted column.
 * @param {Object} data - {id, order_number, table_id, created_at, items}
 */
function addToKitchenBoard(data) {
    const col = document.getElementById('col-accepted');
    if (!col) return;

    const card = document.createElement('article');
    card.className = 'kitchen-card p-5 flex flex-col gap-4';
    card.style.borderLeft = '3px solid var(--staff-blue)';
    card.id = `kcard-${data.id}`;
    card.dataset.orderId = data.id;
    card.dataset.created = data.created_at;

    const itemsHtml = (data.items || []).map(i =>
        `<li class="flex items-start gap-3">
            <span class="font-mono text-xl font-bold shrink-0" style="color: var(--staff-blue);">${i.quantity}x</span>
            <div class="min-w-0">
                <p class="text-lg font-semibold leading-tight">${i.name}</p>
                ${i.notes ? `<p class="text-xs italic mt-1" style="color: var(--staff-muted);">Note: ${i.notes}</p>` : ''}
            </div>
         </li>`
    ).join('');

    card.innerHTML = `
        <div class="flex items-start justify-between gap-3 pb-3" style="border-bottom: 1px solid var(--staff-border);">
            <div>
                <p class="font-mono text-sm font-bold" style="color: var(--staff-blue);">${formatOrderNumber(data.order_number)}</p>
                <p class="text-[10px] uppercase tracking-[0.14em] font-bold mt-1" style="color: var(--staff-muted);">Pending</p>
            </div>
            <span class="staff-chip" style="background: rgba(245,237,231,0.84); color: var(--staff-dark);">${data.table_id ? 'T-' + data.table_id : 'Takeaway'}</span>
        </div>
        <ul class="space-y-3">${itemsHtml}</ul>
        <div class="flex items-center justify-between gap-3 pt-3 mt-auto" style="border-top: 1px solid var(--staff-border);">
            <span class="kitchen-timer text-sm font-mono timer-normal" data-start="${data.created_at}">...</span>
            <button type="button" onclick="markAsPreparing(${data.id})" class="staff-action blue">Begin Prep</button>
        </div>`;

    col.appendChild(card);
    startTimer(card.querySelector('.kitchen-timer'));
    _updateCount('accepted');
}
