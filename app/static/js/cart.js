/**
 * Tablii — Cart management using localStorage.
 */
class Cart {
    /**
     * @param {string} restaurantSlug
     * @param {number} tableId
     */
    constructor(restaurantSlug, tableId) {
        this.storageKey = `tablii_cart_${restaurantSlug}_${tableId}`;
        this.items = [];
        this.load();
    }

    /**
     * Add an item to the cart.
     * @param {Object} item - { id, name, price, quantity, options, image_url }
     */
    addItem(item) {
        this.items.push({
            id: item.id,
            name: item.name,
            price: item.price,
            quantity: item.quantity || 1,
            options: item.options || [],
            image_url: item.image_url || ""
        });
        this.save();
    }

    /**
     * Remove an item by index.
     * @param {number} index
     */
    removeItem(index) {
        this.items.splice(index, 1);
        this.save();
    }

    /**
     * Update quantity at index. Remove if quantity <= 0.
     * @param {number} index
     * @param {number} quantity
     */
    updateQuantity(index, quantity) {
        if (quantity <= 0) {
            this.removeItem(index);
        } else {
            this.items[index].quantity = Math.min(quantity, 20);
            this.save();
        }
    }

    /**
     * Get all cart items.
     * @returns {Array}
     */
    getItems() {
        return this.items;
    }

    /**
     * Calculate subtotal (price + option extras) * quantity for all items.
     * @returns {number}
     */
    getSubtotal() {
        return this.items.reduce((total, item) => {
            const optExtra = (item.options || []).reduce((s, o) => s + (o.extra_price || 0), 0);
            return total + (item.price + optExtra) * item.quantity;
        }, 0);
    }

    /**
     * Calculate tax amount.
     * @param {number} taxRate - percentage (e.g. 7 for 7%)
     * @returns {number}
     */
    getTax(taxRate) {
        return this.getSubtotal() * (taxRate / 100);
    }

    /**
     * Calculate total (subtotal + tax).
     * @param {number} taxRate
     * @returns {number}
     */
    getTotal(taxRate) {
        return this.getSubtotal() + this.getTax(taxRate);
    }

    /**
     * Get total item count.
     * @returns {number}
     */
    getItemCount() {
        return this.items.reduce((count, item) => count + item.quantity, 0);
    }

    /**
     * Empty the cart.
     */
    clear() {
        this.items = [];
        this.save();
    }

    /**
     * Save cart to localStorage.
     */
    save() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.items));
        } catch (e) {
            console.warn("Failed to save cart:", e);
        }
    }

    /**
     * Load cart from localStorage.
     */
    load() {
        try {
            const data = localStorage.getItem(this.storageKey);
            this.items = data ? JSON.parse(data) : [];
        } catch (e) {
            this.items = [];
        }
    }
}
