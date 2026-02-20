/**
 * Tablii — Global JavaScript Utilities
 */

/**
 * Display a toast notification.
 * @param {string} message - The message to display.
 * @param {string} type - 'success' | 'error' | 'info' | 'warning'
 */
function showToast(message, type = "info") {
  const colors = {
    success: "bg-green-500",
    error: "bg-red-500",
    warning: "bg-yellow-500 text-gray-900",
    info: "bg-blue-500",
  };
  const toast = document.createElement("div");
  toast.className = `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-white text-sm ${colors[type] || colors.info}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = "opacity 0.5s";
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 500);
  }, 4000);
}

/**
 * Format a number as Tunisian Dinar currency.
 * @param {number} amount
 * @returns {string}
 */
function formatCurrency(amount) {
  return `${parseFloat(amount).toFixed(3)} TND`;
}

/**
 * Smooth scroll to top of page.
 */
function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}
