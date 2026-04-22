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

        const dot = el.querySelector("div:first-child");
        const label = el.querySelector("div:last-child p:first-child");
        const line = el.querySelector(".absolute");

        // Reset dot styles
        dot.className = "w-8 h-8 rounded-full flex items-center justify-center shrink-0 z-10";

        if (idx < currentIdx) {
            dot.classList.add("bg-orange-500", "text-white");
            dot.textContent = "✓";
            if (label) label.classList.remove("text-gray-400");
            if (label) label.classList.add("text-gray-900");
            if (line) {
                line.classList.remove("bg-gray-200");
                line.classList.add("bg-orange-400");
            }
        } else if (idx === currentIdx) {
            dot.classList.add("bg-orange-500", "text-white", "animate-pulse");
            dot.textContent = "●";
            if (label) label.classList.remove("text-gray-400");
            if (label) label.classList.add("text-gray-900");
        } else {
            dot.classList.add("bg-gray-200", "text-gray-400");
            dot.textContent = "○";
            if (label) label.classList.remove("text-gray-900");
            if (label) label.classList.add("text-gray-400");
            if (line) {
                line.classList.remove("bg-orange-400");
                line.classList.add("bg-gray-200");
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
        accepted: "Your order has been accepted! 🎉",
        preparing: "Your food is being prepared! 👨‍🍳",
        ready: "Your order is ready! 🔔",
        served: "Enjoy your meal! 🍽️",
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
