/**
 * Tablii — Order status tracking utilities.
 * WebSocket connection will be implemented in Phase 8.
 */

const STATUS_STEPS = ["new", "accepted", "preparing", "ready", "served"];

/**
 * Update the order status timeline UI.
 * @param {string} status - Current order status.
 */
function updateOrderStatus(status) {
    const currentIdx = STATUS_STEPS.indexOf(status);
    if (currentIdx === -1) return;

    STATUS_STEPS.forEach((step, idx) => {
        const el = document.querySelector(`[data-step="${step}"]`);
        if (!el) return;

        const dot = el.querySelector(".status-dot");
        const label = el.querySelector(".status-label");
        const line = el.querySelector(".status-line");
        if (!dot) return;

        dot.className = "status-dot z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-black";

        if (idx < currentIdx) {
            dot.classList.add("bg-amber-600", "text-white");
            dot.textContent = "✓";
            if (label) label.classList.remove("text-charcoal-400");
            if (label) label.classList.add("text-charcoal-900");
            if (line) {
                line.classList.remove("bg-cream-300");
                line.classList.add("bg-amber-500");
            }
        } else if (idx === currentIdx) {
            dot.classList.add("bg-charcoal-800", "text-cream-50", "animate-pulse");
            dot.textContent = "●";
            if (label) label.classList.remove("text-charcoal-400");
            if (label) label.classList.add("text-charcoal-900");
        } else {
            dot.classList.add("bg-cream-200", "text-charcoal-400");
            dot.textContent = "○";
            if (label) label.classList.remove("text-charcoal-900");
            if (label) label.classList.add("text-charcoal-400");
            if (line) {
                line.classList.remove("bg-amber-500");
                line.classList.add("bg-cream-300");
            }
        }
    });
}

/**
 * Show a toast notification when status changes.
 * @param {string} status - New order status.
 */
function showStatusNotification(status) {
    const messages = {
        accepted: "Your order has been accepted.",
        preparing: "Your food is being prepared.",
        ready: "Your order is ready.",
        served: "Enjoy your meal.",
    };

    const msg = messages[status];
    if (msg) {
        showToast(msg, "success");

        // Play notification sound for 'ready' status
        if (status === "ready") {
            try {
                const audio = new Audio("/static/sounds/notification.mp3");
                audio.play().catch(() => {});
            } catch (e) {
                // Audio not available
            }
        }
    }
}
