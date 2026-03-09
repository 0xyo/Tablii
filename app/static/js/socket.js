/**
 * socket.js — Shared SocketIO client configuration for all Tablii staff interfaces.
 *
 * Usage: load this AFTER socket.io.js CDN, then call the appropriate connect*() fn.
 */

// ---------------------------------------------------------------------------
// Socket initialization (lazy — only connect when a connect fn is called)
// ---------------------------------------------------------------------------

let socket = null;

function _getSocket() {
    if (!socket) {
        socket = io({ transports: ['websocket', 'polling'] });

        socket.on('connect', () => {
            console.debug('[Tablii] Socket connected:', socket.id);
        });
        socket.on('disconnect', (reason) => {
            console.debug('[Tablii] Socket disconnected:', reason);
        });
        socket.on('connect_error', (err) => {
            console.warn('[Tablii] Socket connection error:', err.message);
        });
    }
    return socket;
}

// ---------------------------------------------------------------------------
// Room helpers
// ---------------------------------------------------------------------------

/** Join the restaurant-wide staff room. */
function connectAsStaff(restaurantId) {
    _getSocket().emit('join_restaurant', { restaurant_id: restaurantId });
}

/** Join the cashier room (+ restaurant room). */
function connectAsCashier(restaurantId) {
    _getSocket().emit('join_cashier', { restaurant_id: restaurantId });
}

/** Join the kitchen room (+ restaurant room). */
function connectAsKitchen(restaurantId) {
    _getSocket().emit('join_kitchen', { restaurant_id: restaurantId });
}

/**
 * Join the waiter personal room + restaurant room.
 * @param {number} restaurantId
 * @param {number} waiterId
 */
function connectAsWaiter(restaurantId, waiterId) {
    _getSocket().emit('join_waiter', { restaurant_id: restaurantId, waiter_id: waiterId });
}

/** Join the customer private tracking room. */
function connectAsCustomer(sessionToken) {
    _getSocket().emit('join_customer', { session_token: sessionToken });
}

/** Subscribe to a specific event. */
function onEvent(event, handler) {
    _getSocket().on(event, handler);
}

// ---------------------------------------------------------------------------
// Sound utilities
// ---------------------------------------------------------------------------

const sounds = {
    new_order:   new Audio('/static/sounds/new_order.mp3'),
    order_ready: new Audio('/static/sounds/order_ready.mp3'),
    call_waiter: new Audio('/static/sounds/call_waiter.wav'),
};

/**
 * Play a named sound, ignoring autoplay restrictions gracefully.
 * @param {'new_order'|'order_ready'|'call_waiter'} type
 */
function playSound(type) {
    const audio = sounds[type];
    if (audio) {
        audio.volume = 0.65;
        audio.currentTime = 0;
        audio.play().catch(() => {});
    }
}
