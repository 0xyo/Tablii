/**
 * menu_builder.js
 * Dashboard: drag-and-drop category/item reordering, image preview, toggle.
 */

'use strict';

// ── 1. initDragDropCategories ───────────────────────────────────────────────

/**
 * Enable drag-and-drop reordering of category rows.
 * Expects rows with data-cat-id attribute inside a container.
 *
 * @param {string} containerId - ID of the <tbody> or list container.
 * @param {string} reorderUrl  - POST URL for /dashboard/menu/categories/reorder.
 */
function initDragDropCategories(containerId = 'category-list', reorderUrl = '/dashboard/menu/categories/reorder') {
  const container = document.getElementById(containerId);
  if (!container) return;

  let dragSrc = null;

  container.querySelectorAll('[data-cat-id]').forEach(row => {
    row.draggable = true;
    row.addEventListener('dragstart', e => {
      dragSrc = row;
      row.classList.add('opacity-50');
      e.dataTransfer.effectAllowed = 'move';
    });
    row.addEventListener('dragend', () => row.classList.remove('opacity-50'));
    row.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });
    row.addEventListener('drop', e => {
      e.preventDefault();
      if (dragSrc && dragSrc !== row) {
        // Swap DOM positions
        const allRows = [...container.querySelectorAll('[data-cat-id]')];
        const srcIdx = allRows.indexOf(dragSrc);
        const dstIdx = allRows.indexOf(row);
        if (srcIdx < dstIdx) {
          container.insertBefore(dragSrc, row.nextSibling);
        } else {
          container.insertBefore(dragSrc, row);
        }
        _saveCategoryOrder(reorderUrl, container);
      }
    });
  });
}

async function _saveCategoryOrder(url, container) {
  const rows = [...container.querySelectorAll('[data-cat-id]')];
  const order = rows.map((r, i) => ({ id: parseInt(r.dataset.catId), sort_order: i }));
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
  try {
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ order }),
    });
  } catch (err) {
    console.error('Category reorder failed:', err);
  }
}

// ── 2. initDragDropItems ───────────────────────────────────────────────────

/**
 * Enable drag-and-drop reordering of menu item rows.
 *
 * @param {string} containerId - ID of the items container.
 */
function initDragDropItems(containerId = 'item-list') {
  const container = document.getElementById(containerId);
  if (!container) return;

  let dragSrc = null;

  container.querySelectorAll('[data-item-id]').forEach(row => {
    row.draggable = true;
    row.addEventListener('dragstart', e => {
      dragSrc = row;
      row.classList.add('opacity-50');
      e.dataTransfer.effectAllowed = 'move';
    });
    row.addEventListener('dragend', () => row.classList.remove('opacity-50'));
    row.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });
    row.addEventListener('drop', e => {
      e.preventDefault();
      if (dragSrc && dragSrc !== row) {
        const allRows = [...container.querySelectorAll('[data-item-id]')];
        const srcIdx = allRows.indexOf(dragSrc);
        const dstIdx = allRows.indexOf(row);
        if (srcIdx < dstIdx) {
          container.insertBefore(dragSrc, row.nextSibling);
        } else {
          container.insertBefore(dragSrc, row);
        }
      }
    });
  });
}

// ── 3. initImagePreview ────────────────────────────────────────────────────

/**
 * Wire up an image file input to show a live preview.
 *
 * @param {string} inputId   - ID of the <input type="file"> element.
 * @param {string} previewId - ID of the <img> element to update.
 */
function initImagePreview(inputId = 'image-input', previewId = 'image-preview') {
  const input   = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  if (!input || !preview) return;

  input.addEventListener('change', () => {
    const file = input.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) return;

    const reader = new FileReader();
    reader.onload = e => {
      preview.src = e.target.result;
      preview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  });
}

// ── 4. toggleAvailability ──────────────────────────────────────────────────

/**
 * Toggle a menu item's availability via AJAX without page reload.
 *
 * @param {number} itemId   - Menu item ID.
 * @param {Element} toggle  - The toggle switch element to update visually.
 */
async function toggleAvailability(itemId, toggle) {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
  try {
    const res = await fetch(`/dashboard/menu/item/${itemId}/toggle`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
    });
    const data = await res.json();
    if (data.success) {
      // Visually flip the toggle
      if (toggle) {
        toggle.checked = data.is_available;
        const label = toggle.closest('label') || toggle.parentElement;
        if (label) {
          label.classList.toggle('bg-green-500', data.is_available);
          label.classList.toggle('bg-gray-300', !data.is_available);
        }
      }
    }
  } catch (err) {
    console.error('toggleAvailability error:', err);
  }
}
