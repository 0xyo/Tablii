/**
 * floor_map.js
 * Interactive canvas-based floor map editor.
 * Tables are rendered as colored draggable rectangles.
 */

'use strict';

// ── Constants ───────────────────────────────────────────────────────────────
const TABLE_W = 80;
const TABLE_H = 60;

const STATUS_COLORS = {
  free:      '#22c55e',  // green-500
  occupied:  '#f97316',  // orange-500
  reserved:  '#ef4444',  // red-500
};

// ── State ───────────────────────────────────────────────────────────────────
let _canvas = null;
let _ctx    = null;
let _tables = [];   // [{id, table_number, status, x, y}, ...]
let _drag = { active: false, tableIdx: -1, offsetX: 0, offsetY: 0 };

// ── 1. renderFloorMap ────────────────────────────────────────────────────────

/**
 * Initialise and render the floor map on a canvas element.
 *
 * @param {string} canvasId - ID of the <canvas> element.
 * @param {Array}  tables   - Array of table objects.
 */
function renderFloorMap(canvasId, tables) {
  _canvas = document.getElementById(canvasId);
  if (!_canvas) return;

  _ctx = _canvas.getContext('2d');
  _tables = tables.map((t, i) => ({
    ...t,
    x: t.pos_x ?? (30 + (i % 5) * 100),
    y: t.pos_y ?? (30 + Math.floor(i / 5) * 90),
  }));

  _canvas.addEventListener('mousedown', _onMouseDown);
  _canvas.addEventListener('mousemove', _onMouseMove);
  _canvas.addEventListener('mouseup',   _onMouseUp);
  _canvas.addEventListener('mouseleave', _onMouseUp);

  _draw();
}

// ── Drawing ──────────────────────────────────────────────────────────────────

function _draw() {
  _ctx.clearRect(0, 0, _canvas.width, _canvas.height);

  // Grid background
  _ctx.strokeStyle = '#e2e8f0';
  _ctx.lineWidth = 1;
  for (let x = 0; x <= _canvas.width; x += 40) {
    _ctx.beginPath(); _ctx.moveTo(x, 0); _ctx.lineTo(x, _canvas.height); _ctx.stroke();
  }
  for (let y = 0; y <= _canvas.height; y += 40) {
    _ctx.beginPath(); _ctx.moveTo(0, y); _ctx.lineTo(_canvas.width, y); _ctx.stroke();
  }

  _tables.forEach(t => {
    const color = STATUS_COLORS[t.status] || STATUS_COLORS.free;
    const radius = 10;

    // Rounded rectangle
    _ctx.beginPath();
    _ctx.moveTo(t.x + radius, t.y);
    _ctx.lineTo(t.x + TABLE_W - radius, t.y);
    _ctx.arcTo(t.x + TABLE_W, t.y, t.x + TABLE_W, t.y + radius, radius);
    _ctx.lineTo(t.x + TABLE_W, t.y + TABLE_H - radius);
    _ctx.arcTo(t.x + TABLE_W, t.y + TABLE_H, t.x + TABLE_W - radius, t.y + TABLE_H, radius);
    _ctx.lineTo(t.x + radius, t.y + TABLE_H);
    _ctx.arcTo(t.x, t.y + TABLE_H, t.x, t.y + TABLE_H - radius, radius);
    _ctx.lineTo(t.x, t.y + radius);
    _ctx.arcTo(t.x, t.y, t.x + radius, t.y, radius);
    _ctx.closePath();

    _ctx.fillStyle = color + '33';    // 20% opacity fill
    _ctx.fill();
    _ctx.strokeStyle = color;
    _ctx.lineWidth = 2;
    _ctx.stroke();

    // Table number label
    _ctx.fillStyle = '#1e293b';
    _ctx.font = 'bold 14px Inter, sans-serif';
    _ctx.textAlign = 'center';
    _ctx.textBaseline = 'middle';
    _ctx.fillText(`T${t.table_number}`, t.x + TABLE_W / 2, t.y + TABLE_H / 2);

    // Status dot
    _ctx.beginPath();
    _ctx.arc(t.x + TABLE_W - 10, t.y + 10, 5, 0, Math.PI * 2);
    _ctx.fillStyle = color;
    _ctx.fill();
  });
}

// ── 2. dragTable ─────────────────────────────────────────────────────────────

/**
 * Update a table's position (called internally during mouse move).
 */
function dragTable(tableId, newX, newY) {
  const t = _tables.find(t => t.id === tableId);
  if (!t) return;
  t.x = Math.max(0, Math.min(newX, _canvas.width  - TABLE_W));
  t.y = Math.max(0, Math.min(newY, _canvas.height - TABLE_H));
  _draw();
}

// ── 3. saveFloorLayout ───────────────────────────────────────────────────────

/**
 * POST the current table positions to the server.
 *
 * @param {string} url - Endpoint URL (default: /dashboard/tables/layout).
 */
async function saveFloorLayout(url = '/dashboard/tables/layout') {
  const positions = _tables.map(t => ({ id: t.id, pos_x: t.x, pos_y: t.y }));
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ positions }),
    });
    const data = await res.json();
    if (!data.success) console.warn('saveFloorLayout: server returned failure');
  } catch (err) {
    console.error('saveFloorLayout error:', err);
  }
}

// ── Mouse event handlers ──────────────────────────────────────────────────────

function _getMousePos(e) {
  const rect = _canvas.getBoundingClientRect();
  return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}

function _hitTest(pos) {
  return _tables.findIndex(t =>
    pos.x >= t.x && pos.x <= t.x + TABLE_W &&
    pos.y >= t.y && pos.y <= t.y + TABLE_H
  );
}

function _onMouseDown(e) {
  const pos = _getMousePos(e);
  const idx = _hitTest(pos);
  if (idx >= 0) {
    _drag = {
      active: true,
      tableIdx: idx,
      offsetX: pos.x - _tables[idx].x,
      offsetY: pos.y - _tables[idx].y,
    };
    _canvas.style.cursor = 'grabbing';
  }
}

function _onMouseMove(e) {
  const pos = _getMousePos(e);
  if (_drag.active) {
    const t = _tables[_drag.tableIdx];
    dragTable(t.id, pos.x - _drag.offsetX, pos.y - _drag.offsetY);
  } else {
    _canvas.style.cursor = _hitTest(pos) >= 0 ? 'grab' : 'default';
  }
}

function _onMouseUp() {
  if (_drag.active) {
    _drag.active = false;
    _canvas.style.cursor = 'default';
    saveFloorLayout();
  }
}
