/**
 * analytics_charts.js
 * Chart.js helpers for the analytics dashboard.
 * Each function creates or replaces a chart on the given canvas ID.
 */

'use strict';

// ── Shared palette ─────────────────────────────────────────────────────────
const CHART_COLORS = {
  orange:      'rgba(251, 146, 60, 1)',
  orangeFill:  'rgba(251, 146, 60, 0.15)',
  blue:        'rgba(59, 130, 246, 1)',
  green:       'rgba(34, 197, 94, 1)',
  red:         'rgba(239, 68, 68, 1)',
  purple:      'rgba(168, 85, 247, 1)',
  yellow:      'rgba(234, 179, 8, 1)',
  teal:        'rgba(20, 184, 166, 1)',
  pink:        'rgba(236, 72, 153, 1)',
  indigo:      'rgba(99, 102, 241, 1)',
  statusColors: {
    new:        'rgba(59, 130, 246, 0.8)',
    accepted:   'rgba(234, 179, 8, 0.8)',
    preparing:  'rgba(251, 146, 60, 0.8)',
    ready:      'rgba(20, 184, 166, 0.8)',
    served:     'rgba(34, 197, 94, 0.8)',
    completed:  'rgba(34, 197, 94, 0.8)',
    cancelled:  'rgba(239, 68, 68, 0.8)',
  },
};

// Keep a registry so we can destroy charts before re-creating
const _instances = {};

function _destroyIfExists(canvasId) {
  if (_instances[canvasId]) {
    _instances[canvasId].destroy();
    delete _instances[canvasId];
  }
}

// ── 1. Revenue Line Chart ───────────────────────────────────────────────────
/**
 * Render a line chart showing daily revenue over the selected period.
 *
 * @param {string} canvasId  - DOM id of the <canvas> element.
 * @param {Array}  data      - Array of {date, revenue, orders} objects.
 */
function renderRevenueChart(canvasId, data) {
  _destroyIfExists(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const labels   = data.map(d => d.date);
  const revenues = data.map(d => d.revenue);

  _instances[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Revenue (TND)',
        data: revenues,
        borderColor: CHART_COLORS.orange,
        backgroundColor: CHART_COLORS.orangeFill,
        borderWidth: 2.5,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${Number(ctx.parsed.y).toFixed(3)} TND`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', maxTicksLimit: 8 },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: {
            color: '#94a3b8',
            callback: v => v.toFixed(3),
          },
          beginAtZero: true,
        },
      },
    },
  });
}

// ── 2. Top Items Horizontal Bar Chart ──────────────────────────────────────
/**
 * Render a horizontal bar chart for the top-selling menu items.
 *
 * @param {string} canvasId
 * @param {Array}  data      - Array of {name, quantity_sold, revenue}.
 */
function renderTopItemsChart(canvasId, data) {
  _destroyIfExists(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const barColors = [
    CHART_COLORS.orange, CHART_COLORS.blue, CHART_COLORS.green,
    CHART_COLORS.purple, CHART_COLORS.teal, CHART_COLORS.pink,
    CHART_COLORS.yellow, CHART_COLORS.red, CHART_COLORS.indigo,
    CHART_COLORS.orange,
  ];

  _instances[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.name),
      datasets: [{
        label: 'Units Sold',
        data: data.map(d => d.quantity_sold),
        backgroundColor: barColors.slice(0, data.length),
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' },
          beginAtZero: true,
        },
        y: {
          grid: { display: false },
          ticks: { color: '#94a3b8' },
        },
      },
    },
  });
}

// ── 3. Peak Hours Vertical Bar Chart ───────────────────────────────────────
/**
 * Render a bar chart of order count by hour of day.
 *
 * @param {string} canvasId
 * @param {Array}  data      - Array of {hour, count} for hours 0–23.
 */
function renderPeakHoursChart(canvasId, data) {
  _destroyIfExists(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const maxCount = Math.max(...data.map(d => d.count), 1);

  _instances[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => `${String(d.hour).padStart(2, '0')}:00`),
      datasets: [{
        label: 'Orders',
        data: data.map(d => d.count),
        backgroundColor: data.map(d => {
          const opacity = 0.2 + 0.7 * (d.count / maxCount);
          return `rgba(251, 146, 60, ${opacity.toFixed(2)})`;
        }),
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8', maxRotation: 45 },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' },
          beginAtZero: true,
        },
      },
    },
  });
}

// ── 4. Order Status Doughnut Chart ─────────────────────────────────────────
/**
 * Render a doughnut chart for order status distribution.
 *
 * @param {string} canvasId
 * @param {Object} data      - {status: count} mapping.
 */
function renderOrderStatusChart(canvasId, data) {
  _destroyIfExists(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const statuses = Object.keys(data);
  const counts   = statuses.map(s => data[s]);
  const colors   = statuses.map(s => CHART_COLORS.statusColors[s] || CHART_COLORS.blue);

  _instances[canvasId] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: statuses.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
      datasets: [{
        data: counts,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#1e293b',
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#94a3b8',
            padding: 14,
            font: { size: 12 },
          },
        },
      },
      cutout: '60%',
    },
  });
}
