import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';
import exec from 'k6/execution';

const BASE_URL = (__ENV.BASE_URL || 'http://127.0.0.1:5000').replace(/\/+$/, '');
const SLUG = __ENV.SLUG || 'chez-ahmed';
const LANG = __ENV.LANG || 'fr';
const TABLE_IDS = parseTables(__ENV.TABLES || '1-8');
const MODE = (__ENV.MODE || 'load').toLowerCase();
const WORKLOAD = (__ENV.WORKLOAD || 'mixed').toLowerCase();
const VUS = positiveInt(__ENV.VUS, 25);
const DURATION = __ENV.DURATION || '1m';
const RAMP_UP = __ENV.RAMP_UP || '15s';
const RAMP_DOWN = __ENV.RAMP_DOWN || '10s';
const STRESS_STAGES = __ENV.STRESS_STAGES || '10:30s,25:45s,50:45s,100:45s';
const MIN_SLEEP = positiveNumber(__ENV.MIN_SLEEP, 0.1);
const MAX_SLEEP = positiveNumber(__ENV.MAX_SLEEP, 1.0);
const MAX_ITEMS_PER_ORDER = positiveInt(__ENV.MAX_ITEMS_PER_ORDER, 2);
const MAX_QUANTITY = Math.min(positiveInt(__ENV.MAX_QUANTITY, 3), 20);
const FAIL_RATE = positiveNumber(__ENV.FAIL_RATE, 0.05);
const P95_MS = positiveInt(__ENV.P95_MS, 1500);

const writesEnabled = WORKLOAD === 'mixed' || WORKLOAD === 'orders';

if (!['load', 'stress'].includes(MODE)) {
  throw new Error(`MODE must be "load" or "stress", got "${MODE}"`);
}

if (!['read', 'mixed', 'orders'].includes(WORKLOAD)) {
  throw new Error(`WORKLOAD must be "read", "mixed", or "orders", got "${WORKLOAD}"`);
}

if (writesEnabled && !isLocalTarget(BASE_URL) && __ENV.ALLOW_NON_LOCAL_WRITES !== '1') {
  throw new Error(
    'Refusing to create orders against a non-local target. ' +
      'Use WORKLOAD=read or set ALLOW_NON_LOCAL_WRITES=1 when you have permission and a cleanup plan.',
  );
}

export const options = {
  scenarios: {
    restaurant: MODE === 'stress'
      ? {
          executor: 'ramping-vus',
          gracefulRampDown: '10s',
          stages: parseStressStages(STRESS_STAGES),
        }
      : {
          executor: 'ramping-vus',
          gracefulRampDown: '10s',
          stages: [
            { duration: RAMP_UP, target: VUS },
            { duration: DURATION, target: VUS },
            { duration: RAMP_DOWN, target: 0 },
          ],
        },
  },
  thresholds: {
    checks: [`rate>${1 - FAIL_RATE}`],
    http_req_failed: [`rate<${FAIL_RATE}`],
    http_req_duration: [`p(95)<${P95_MS}`],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

const ordersCreated = new Counter('orders_created');
const waiterCallsCreated = new Counter('waiter_calls_created');
const placeOrderFailures = new Rate('place_order_failures');

let lastOrderId = null;

export function setup() {
  const res = http.get(`${BASE_URL}/api/restaurant/${SLUG}/menu?lang=${LANG}`, {
    tags: { name: 'GET /api/restaurant/:slug/menu' },
  });

  check(res, {
    'setup menu is available': (r) => r.status === 200,
  });

  if (res.status !== 200) {
    throw new Error(`Could not fetch menu from ${BASE_URL}; status=${res.status}`);
  }

  const menu = res.json();
  const items = [];
  for (const category of menu.categories || []) {
    for (const item of category.items || []) {
      if (item.is_available !== false) {
        items.push(item);
      }
    }
  }

  if (items.length === 0) {
    throw new Error(`No available menu items found for restaurant slug "${SLUG}"`);
  }

  return { items };
}

export default function (data) {
  const task = chooseTask();

  if (task === 'browse') {
    browseMenu(data.items);
  } else if (task === 'order') {
    orderJourney(data.items);
  } else if (task === 'status') {
    pollOrderStatus(data.items);
  } else {
    callWaiter();
  }

  sleep(randomBetween(MIN_SLEEP, MAX_SLEEP));
}

function browseMenu(items) {
  const tableId = randomTable();

  http.get(`${BASE_URL}/api/restaurant/${SLUG}/menu?lang=${LANG}`, {
    tags: { name: 'GET /api/restaurant/:slug/menu' },
  });

  if (Math.random() < 0.45) {
    const item = randomChoice(items);
    http.get(`${BASE_URL}/api/menu-item/${item.id}?lang=${LANG}`, {
      tags: { name: 'GET /api/menu-item/:id' },
    });
  }

  if (Math.random() < 0.35) {
    http.get(`${BASE_URL}/r/${SLUG}/table/${tableId}`, {
      tags: { name: 'GET /r/:slug/table/:id' },
    });
  }

  if (Math.random() < 0.2) {
    http.get(`${BASE_URL}/r/${SLUG}/table/${tableId}/cart`, {
      tags: { name: 'GET /r/:slug/table/:id/cart' },
    });
  }
}

function orderJourney(items) {
  const tableId = randomTable();

  const menuPage = http.get(`${BASE_URL}/r/${SLUG}/table/${tableId}`, {
    tags: { name: 'GET /r/:slug/table/:id' },
  });
  if (menuPage.status >= 400) {
    return;
  }

  http.post(
    `${BASE_URL}/r/${SLUG}/table/${tableId}/identify`,
    JSON.stringify({
      name: `Load User ${exec.vu.idInTest}`,
      phone: `+21620${String(exec.vu.idInTest % 1000000).padStart(6, '0')}`,
    }),
    jsonParams('POST /identify'),
  );

  const order = http.post(
    `${BASE_URL}/r/${SLUG}/table/${tableId}/order`,
    JSON.stringify({
      items: buildOrderItems(items),
      payment_method: 'cash',
      special_notes: `k6 load test vu=${exec.vu.idInTest}`,
      is_gift: false,
    }),
    jsonParams('POST /order'),
  );

  let body = {};
  try {
    body = order.json();
  } catch (error) {
    body = {};
  }

  const created = check(order, {
    'order created': (r) => r.status === 200 && body.success === true && Number.isInteger(body.order_id),
  });

  placeOrderFailures.add(!created);
  if (!created) {
    return;
  }

  ordersCreated.add(1);
  lastOrderId = body.order_id;

  http.get(`${BASE_URL}/api/order/${lastOrderId}/status`, {
    tags: { name: 'GET /api/order/:id/status' },
  });

  if (Math.random() < 0.35) {
    http.get(`${BASE_URL}/r/${SLUG}/table/${tableId}/track/${lastOrderId}`, {
      tags: { name: 'GET /track/:order_id' },
    });
  }
}

function pollOrderStatus(items) {
  if (!lastOrderId) {
    browseMenu(items);
    return;
  }

  http.get(`${BASE_URL}/api/order/${lastOrderId}/status`, {
    tags: { name: 'GET /api/order/:id/status' },
  });
}

function callWaiter() {
  const tableId = randomTable();
  http.get(`${BASE_URL}/r/${SLUG}/table/${tableId}`, {
    tags: { name: 'GET /r/:slug/table/:id' },
  });

  const res = http.post(
    `${BASE_URL}/r/${SLUG}/table/${tableId}/call-waiter`,
    JSON.stringify({ call_type: randomChoice(['water', 'bill', 'help']) }),
    jsonParams('POST /call-waiter'),
  );

  if (res.status < 400) {
    waiterCallsCreated.add(1);
  }
}

function buildOrderItems(items) {
  const count = randomInt(1, Math.min(MAX_ITEMS_PER_ORDER, items.length));
  const shuffled = [...items].sort(() => Math.random() - 0.5);

  return shuffled.slice(0, count).map((item) => ({
    menu_item_id: item.id,
    quantity: randomInt(1, MAX_QUANTITY),
    selected_options: selectedOptionsFor(item),
    notes: '',
  }));
}

function selectedOptionsFor(item) {
  const selected = [];
  for (const group of item.customizations || []) {
    const options = group.options || [];
    if (options.length === 0) {
      continue;
    }

    const defaultOption = options.find((option) => option.is_default) || options[0];
    if (group.required || Math.random() < 0.15) {
      selected.push(defaultOption.id);
    }
  }
  return selected;
}

function chooseTask() {
  const roll = Math.random();

  if (WORKLOAD === 'read') {
    return 'browse';
  }

  if (WORKLOAD === 'orders') {
    return roll < 0.85 ? 'order' : 'status';
  }

  if (roll < 0.5) {
    return 'browse';
  }
  if (roll < 0.85) {
    return 'order';
  }
  if (roll < 0.95) {
    return 'status';
  }
  return 'waiter';
}

function jsonParams(name) {
  return {
    headers: { 'Content-Type': 'application/json' },
    tags: { name },
  };
}

function parseTables(value) {
  const tables = [];
  for (const part of value.split(',')) {
    const token = part.trim();
    if (!token) {
      continue;
    }

    if (token.includes('-')) {
      const [startRaw, endRaw] = token.split('-', 2);
      const start = Number.parseInt(startRaw, 10);
      const end = Number.parseInt(endRaw, 10);
      if (!Number.isInteger(start) || !Number.isInteger(end) || end < start) {
        throw new Error(`Invalid TABLES range "${token}"`);
      }
      for (let table = start; table <= end; table += 1) {
        tables.push(table);
      }
    } else {
      const table = Number.parseInt(token, 10);
      if (!Number.isInteger(table)) {
        throw new Error(`Invalid TABLES value "${token}"`);
      }
      tables.push(table);
    }
  }

  const unique = [...new Set(tables)];
  if (unique.length === 0) {
    throw new Error('TABLES must include at least one table id');
  }
  return unique;
}

function parseStressStages(value) {
  return value.split(',').map((stage) => {
    const [targetRaw, durationRaw] = stage.split(':', 2);
    const target = Number.parseInt(targetRaw, 10);
    const duration = (durationRaw || '').trim();
    if (!Number.isInteger(target) || target < 0 || !duration) {
      throw new Error(`Invalid STRESS_STAGES entry "${stage}". Use target:duration, for example 25:1m.`);
    }
    return { target, duration };
  });
}

function isLocalTarget(url) {
  const normalized = url.toLowerCase();
  return (
    normalized.includes('//127.0.0.1') ||
    normalized.includes('//localhost') ||
    normalized.includes('//[::1]')
  );
}

function randomTable() {
  return randomChoice(TABLE_IDS);
}

function randomChoice(values) {
  return values[randomInt(0, values.length - 1)];
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomBetween(min, max) {
  return Math.random() * (max - min) + min;
}

function positiveInt(value, fallback) {
  if (value === undefined || value === '') {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`Expected a positive integer, got "${value}"`);
  }
  return parsed;
}

function positiveNumber(value, fallback) {
  if (value === undefined || value === '') {
    return fallback;
  }
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`Expected a positive number, got "${value}"`);
  }
  return parsed;
}
