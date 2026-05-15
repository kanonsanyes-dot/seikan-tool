const GANTT = {
  DAY_WIDTH: 32,
  RANGE_DAYS: 60,
  DRAG_THRESHOLD: 3,
};

const els = {
  table: document.getElementById('ganttTable'),
  scroll: document.getElementById('ganttScroll'),
  rangeLabel: document.getElementById('ganttRangeLabel'),
  flash: document.getElementById('ganttFlash'),
  prev: document.getElementById('ganttPrev'),
  today: document.getElementById('ganttToday'),
  next: document.getElementById('ganttNext'),
};

const state = {
  orders: [],
  today: toDateOnly(new Date()),
  rangeStart: toDateOnly(new Date()),
  collapsed: new Set(),
};

function parseDate(value) {
  return new Date(`${value}T00:00:00`);
}

function toDateOnly(date) {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  return d.toISOString().slice(0, 10);
}

function fmtDate(date) {
  return date.toISOString().slice(0, 10);
}

function addDays(value, days) {
  const date = typeof value === 'string' ? parseDate(value) : new Date(value);
  date.setDate(date.getDate() + days);
  return fmtDate(date);
}

function daysBetween(start, end) {
  return Math.round((parseDate(end) - parseDate(start)) / 86400000);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function rangeEnd() {
  return addDays(state.rangeStart, GANTT.RANGE_DAYS - 1);
}

function dateAtOffset(offset) {
  return addDays(state.rangeStart, offset);
}

function offsetPx(date) {
  return daysBetween(state.rangeStart, date) * GANTT.DAY_WIDTH;
}

function widthPx(start, end) {
  return (daysBetween(start, end) + 1) * GANTT.DAY_WIDTH;
}

function statusClass(process) {
  if (process.end_date && process.end_date < state.today && process.status !== '完了') return 'late';
  if (process.status === '完了') return 'done';
  if (process.status === '進行中') return 'active';
  if (process.status === '遅延') return 'late';
  return 'not-started';
}

function statusLabel(process) {
  return statusClass(process) === 'late' ? '遅延' : (process.status || '未着手');
}

function showFlash(message) {
  els.flash.textContent = message;
  els.flash.classList.remove('d-none');
  window.setTimeout(() => els.flash.classList.add('d-none'), 4200);
}

async function loadData() {
  const res = await fetch('/api/progress/gantt');
  if (!res.ok) throw new Error(`load failed: ${res.status}`);
  const data = await res.json();
  state.orders = data.orders || [];
  state.today = data.today || toDateOnly(new Date());
  state.rangeStart = state.today;
  render();
}

function makeEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function render() {
  els.table.innerHTML = '';
  els.table.style.setProperty('--timeline-width', `${GANTT.DAY_WIDTH * GANTT.RANGE_DAYS}px`);
  els.rangeLabel.textContent = `${state.rangeStart} 〜 ${rangeEnd()}`;

  renderHeader();
  if (!state.orders.length) {
    els.table.appendChild(makeEl('div', 'gantt-empty', '進捗データがありません。スケジューラーで工程を生成すると表示されます。'));
    return;
  }

  state.orders.forEach(order => {
    renderOrderRow(order);
    if (!state.collapsed.has(order.order_id)) {
      order.processes.forEach(process => renderProcessRow(order, process));
    }
  });
}

function renderHeader() {
  const row = makeEl('div', 'gantt-row gantt-row-header');
  row.appendChild(makeEl('div', 'gantt-label gantt-header-label', '受注 / 工程'));
  const canvas = makeEl('div', 'gantt-canvas gantt-header-canvas');

  for (let i = 0; i < GANTT.RANGE_DAYS; i += 1) {
    const date = parseDate(dateAtOffset(i));
    const cell = makeEl('div', 'gantt-date-cell');
    const isFirstDay = date.getDate() === 1;
    cell.textContent = isFirstDay ? `${date.getMonth() + 1}月${date.getDate()}日` : `${date.getMonth() + 1}/${date.getDate()}`;
    if (date.getDay() === 0 || date.getDay() === 6) cell.classList.add('is-weekend');
    if (fmtDate(date) === state.today) cell.classList.add('is-today');
    canvas.appendChild(cell);
  }
  row.appendChild(canvas);
  els.table.appendChild(row);
}

function renderOrderRow(order) {
  const row = makeEl('div', 'gantt-row gantt-order-row');
  const label = makeEl('div', 'gantt-label gantt-order-label');
  const marker = state.collapsed.has(order.order_id) ? '▸' : '▾';
  label.innerHTML = `
    <div>
      <div class="gantt-order-title">${marker} #${order.order_id} ${escapeHtml(order.product_name || '')}</div>
      <div class="gantt-order-meta">${escapeHtml(order.customer || '')} / 出荷日 ${order.ship_date || '-'}</div>
    </div>`;
  label.addEventListener('click', () => {
    if (state.collapsed.has(order.order_id)) state.collapsed.delete(order.order_id);
    else state.collapsed.add(order.order_id);
    render();
  });
  row.appendChild(label);

  const canvas = makeEl('div', 'gantt-canvas');
  appendCalendarGuides(canvas, order.ship_date);
  row.appendChild(canvas);
  els.table.appendChild(row);
}

function renderProcessRow(order, process) {
  const row = makeEl('div', 'gantt-row gantt-process-row');
  const label = makeEl('div', 'gantt-label gantt-process-label');
  label.innerHTML = `
    <span class="gantt-process-name">${escapeHtml(process.process_name || '')}</span>
    <span class="gantt-status-badge gantt-status-${statusClass(process)}">${escapeHtml(statusLabel(process))}</span>`;
  row.appendChild(label);

  const canvas = makeEl('div', 'gantt-canvas');
  appendCalendarGuides(canvas, order.ship_date);
  if (process.start_date && process.end_date) {
    const bar = makeEl('div', `gantt-bar ${statusClass(process)}`);
    bar.dataset.progressId = process.progress_id;
    bar.style.left = `${offsetPx(process.start_date)}px`;
    bar.style.width = `${widthPx(process.start_date, process.end_date)}px`;
    bar.title = `${process.process_name}: ${process.start_date} 〜 ${process.end_date}`;
    canvas.appendChild(bar);
    attachDrag(bar, process);
  }
  row.appendChild(canvas);
  els.table.appendChild(row);
}

function appendCalendarGuides(canvas, shipDate) {
  for (let i = 0; i < GANTT.RANGE_DAYS; i += 1) {
    const key = dateAtOffset(i);
    const d = parseDate(key);
    if (d.getDay() === 0 || d.getDay() === 6) {
      const bg = makeEl('div', 'weekend-bg');
      bg.style.left = `${i * GANTT.DAY_WIDTH}px`;
      canvas.appendChild(bg);
    }
    if (key === state.today) {
      const bg = makeEl('div', 'today-bg');
      bg.style.left = `${i * GANTT.DAY_WIDTH}px`;
      canvas.appendChild(bg);
      const line = makeEl('div', 'today-line');
      line.style.left = `${i * GANTT.DAY_WIDTH}px`;
      canvas.appendChild(line);
    }
    if (shipDate && key === shipDate) {
      const line = makeEl('div', 'ship-line');
      line.style.left = `${i * GANTT.DAY_WIDTH}px`;
      canvas.appendChild(line);
    }
  }
}

function attachDrag(bar, process) {
  const gesture = {
    pointerId: null,
    startX: 0,
    origLeft: 0,
    origStart: process.start_date,
    origEnd: process.end_date,
    durationDays: daysBetween(process.start_date, process.end_date) + 1,
    started: false,
    nextStart: process.start_date,
    nextEnd: process.end_date,
  };

  function cleanupTip() {
    bar.querySelector('.gantt-bar-tip')?.remove();
  }

  function updateTip() {
    let tip = bar.querySelector('.gantt-bar-tip');
    if (!tip) {
      tip = makeEl('span', 'gantt-bar-tip');
      bar.appendChild(tip);
    }
    tip.textContent = `${gesture.nextStart} 〜 ${gesture.nextEnd}`;
  }

  function moveTo(leftPx) {
    const maxLeft = (GANTT.RANGE_DAYS - gesture.durationDays) * GANTT.DAY_WIDTH;
    const snappedLeft = clamp(Math.round(leftPx / GANTT.DAY_WIDTH) * GANTT.DAY_WIDTH, 0, Math.max(0, maxLeft));
    const startOffset = Math.round(snappedLeft / GANTT.DAY_WIDTH);
    gesture.nextStart = dateAtOffset(startOffset);
    gesture.nextEnd = dateAtOffset(startOffset + gesture.durationDays - 1);
    bar.style.left = `${snappedLeft}px`;
    updateTip();
  }

  bar.addEventListener('pointerdown', e => {
    gesture.pointerId = e.pointerId;
    gesture.startX = e.clientX;
    gesture.origLeft = parseFloat(bar.style.left || '0');
    gesture.origStart = process.start_date;
    gesture.origEnd = process.end_date;
    gesture.started = false;
    bar.setPointerCapture(e.pointerId);
    bar.classList.add('dragging');
    e.preventDefault();
  });

  bar.addEventListener('pointermove', e => {
    if (gesture.pointerId !== e.pointerId) return;
    const dx = e.clientX - gesture.startX;
    if (!gesture.started && Math.abs(dx) >= GANTT.DRAG_THRESHOLD) gesture.started = true;
    if (gesture.started) moveTo(gesture.origLeft + dx);
    e.preventDefault();
  });

  bar.addEventListener('pointercancel', e => {
    if (gesture.pointerId !== e.pointerId) return;
    try { bar.releasePointerCapture?.(e.pointerId); } catch (_) {}
    bar.style.left = `${gesture.origLeft}px`;
    bar.classList.remove('dragging');
    cleanupTip();
    gesture.pointerId = null;
  });

  bar.addEventListener('pointerup', async e => {
    if (gesture.pointerId !== e.pointerId) return;
    try { bar.releasePointerCapture?.(e.pointerId); } catch (_) {}
    bar.classList.remove('dragging');
    cleanupTip();
    gesture.pointerId = null;

    if (!gesture.started) {
      bar.style.left = `${gesture.origLeft}px`;
      return;
    }

    const savedStart = process.start_date;
    const savedEnd = process.end_date;
    process.start_date = gesture.nextStart;
    process.end_date = gesture.nextEnd;

    try {
      const res = await fetch(`/api/progress/gantt/${process.progress_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_date: process.start_date, end_date: process.end_date }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `save failed: ${res.status}`);
      }
      render();
    } catch (err) {
      process.start_date = savedStart;
      process.end_date = savedEnd;
      bar.style.left = `${gesture.origLeft}px`;
      showFlash(`日程の保存に失敗しました: ${err.message}`);
    }
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

els.prev.addEventListener('click', () => {
  state.rangeStart = addDays(state.rangeStart, -GANTT.RANGE_DAYS);
  render();
});

els.today.addEventListener('click', () => {
  state.rangeStart = state.today;
  render();
});

els.next.addEventListener('click', () => {
  state.rangeStart = addDays(state.rangeStart, GANTT.RANGE_DAYS);
  render();
});

loadData().catch(err => {
  console.error(err);
  showFlash('ガントチャートデータの読み込みに失敗しました。');
});
