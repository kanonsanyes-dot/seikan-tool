const CONFIG = {
  DAY_WIDTH: 24,
  ROW_HEIGHT: 54,
  SNAP_THRESHOLD_DAYS: 3,
  DRAG_START_THRESHOLD: 3,
  SETTLE_MS: 160,
};

const PROCESS_COLORS = {
  'プレス': { bg: '#EEEDFE', border: '#7F77DD', text: '#3C3489' },
  'バレル': { bg: '#E1F5EE', border: '#1D9E75', text: '#085041' },
  'めっき': { bg: '#E6F1FB', border: '#378ADD', text: '#0C447C' },
  '外観検査': { bg: '#FAEEDA', border: '#BA7517', text: '#633806' },
  '出荷': { bg: '#EAF3DE', border: '#639922', text: '#27500A' },
};

const els = {
  month: document.getElementById('month'),
  customer: document.getElementById('customer'),
  product: document.getElementById('product'),
  snap: document.getElementById('snap'),
  timeline: document.getElementById('timeline'),
  summary: document.getElementById('summary'),
  loadWarnings: document.getElementById('loadWarnings'),
  orderSelect: document.getElementById('orderSelect'),
  generateForm: document.getElementById('generateForm'),
  btnLoad: document.getElementById('btn-load'),
  btnPdf: document.getElementById('btn-pdf'),
};

const state = {
  orders: [],
  schedules: [],
  start: null,
  end: null,
  snapEnabled: true,
  filters: {},
  activeGesture: null,
  qualityAbort: null,
};

function parseDate(s) { return new Date(`${s}T00:00:00`); }
function fmtDate(d) { return d.toISOString().slice(0, 10); }
function daysBetween(a, b) { return Math.round((parseDate(b) - parseDate(a)) / 86400000); }
function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }
function offsetPx(date) { return daysBetween(state.start, date) * CONFIG.DAY_WIDTH; }
function widthPx(s, e) { return (daysBetween(s, e) + 1) * CONFIG.DAY_WIDTH; }
function pxToDay(px) { return Math.round(px / CONFIG.DAY_WIDTH); }
function dateByOffset(dayOffset) {
  return fmtDate(new Date(parseDate(state.start).getTime() + dayOffset * 86400000));
}
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function loadAndRender() {
  state.filters = {
    month: els.month.value,
    customer: els.customer.value,
    product: els.product.value,
  };
  state.snapEnabled = els.snap.checked;

  const res = await fetch(`/api/scheduler/data?${new URLSearchParams(state.filters)}`);
  const data = await res.json();
  state.orders = data.orders || [];
  state.schedules = data.schedules || [];
  state.start = data.range?.start || fmtDate(new Date());
  state.end = data.range?.end || fmtDate(new Date(Date.now() + 90 * 86400000));

  renderTimeline();
  await applyQualityFlags(state.orders.map(o => o.order_id));
}

function renderTimeline() {
  // ドラッグ中は全体再描画しない。保存後だけここに戻る。
  state.activeGesture = null;
  els.timeline.innerHTML = '';
  els.summary.textContent = `受注 ${state.orders.length}件 / 工程カード ${state.schedules.length}件`;
  renderHeader(els.timeline);
  state.orders.forEach(order => renderRow(els.timeline, order));
  renderLoadWarnings();
}

function renderHeader(tl) {
  const row = document.createElement('div');
  row.className = 'timeline-header';
  row.innerHTML = '<div class="timeline-label">受注情報</div><div class="timeline-canvas month-head"></div>';
  const canvas = row.querySelector('.timeline-canvas');
  let d = parseDate(state.start);
  const end = parseDate(state.end);
  while (d <= end) {
    const cell = document.createElement('div');
    cell.className = 'month-cell';
    cell.style.width = `${CONFIG.DAY_WIDTH * 15}px`;
    cell.textContent = `${d.getMonth() + 1}/${d.getDate()}`;
    canvas.appendChild(cell);
    d.setDate(d.getDate() + 15);
  }
  tl.appendChild(row);
}

function renderRow(tl, order) {
  const row = document.createElement('div');
  row.className = 'timeline-row';
  row.dataset.orderId = order.order_id;
  row.innerHTML = `
    <div class="timeline-label">
      <b>#${order.order_id}</b> ${order.product_name}<br>
      ${order.customer} / ${order.ship_date} / ${order.quantity}
    </div>
    <div class="timeline-canvas"></div>`;

  const canvas = row.querySelector('.timeline-canvas');
  const line = document.createElement('div');
  line.className = 'ship-line';
  line.style.left = `${offsetPx(order.ship_date)}px`;
  canvas.appendChild(line);

  state.schedules
    .filter(s => s.order_id === order.order_id)
    .forEach(schedule => {
      const color = PROCESS_COLORS[schedule.process_name] || { bg: '#e2e8f0', border: '#64748b', text: '#111827' };
      const card = document.createElement('div');
      card.className = `proc-card${schedule.locked ? ' locked' : ''}`;
      card.dataset.scheduleId = schedule.schedule_id;
      card.dataset.orderId = schedule.order_id;
      card.style.left = `${offsetPx(schedule.start_date)}px`;
      card.style.width = `${widthPx(schedule.start_date, schedule.end_date)}px`;
      card.style.background = color.bg;
      card.style.borderColor = color.border;
      card.style.color = color.text;
      card.innerHTML = `
        <span class="resize-handle left" data-handle="left" aria-label="開始日を変更"></span>
        <span class="card-title">${schedule.process_name}</span>
        <span class="load-badge">${schedule.required_days || ''}日</span>
        <span class="resize-handle right" data-handle="right" aria-label="終了日を変更"></span>`;
      canvas.appendChild(card);
      attachDrag(card, schedule);
    });

  tl.appendChild(row);
}

function attachDrag(cardEl, schedule) {
  let rafId = null;
  const gesture = {
    mode: null,
    pointerId: null,
    startX: 0,
    origLeft: 0,
    origWidth: 0,
    rawDx: 0,
    dayDx: 0,
    nextLeft: 0,
    nextWidth: 0,
    started: false,
    saving: false,
  };

  function resetGestureState() {
    gesture.mode = null;
    gesture.pointerId = null;
    gesture.rawDx = 0;
    gesture.dayDx = 0;
    gesture.started = false;
    state.activeGesture = null;
  }

  function cleanupGestureClasses() {
    cardEl.classList.remove('dragging', 'drag-active', 'settling', 'saving', 'snapped', 'save-error');
    cardEl.style.cursor = schedule.locked ? 'not-allowed' : 'grab';
    removeFloatingDateTip(cardEl);
  }

  function applyPreview() {
    rafId = null;
    const minW = CONFIG.DAY_WIDTH;
    const dayDelta = pxToDay(gesture.rawDx);
    gesture.dayDx = dayDelta;

    if (gesture.mode === 'move') {
      const proposedLeft = clamp(gesture.origLeft + dayDelta * CONFIG.DAY_WIDTH, 0, Number.MAX_SAFE_INTEGER);
      gesture.nextLeft = proposedLeft;
      gesture.nextWidth = gesture.origWidth;
      cardEl.style.transform = `translateX(${proposedLeft - gesture.origLeft}px)`;
    } else if (gesture.mode === 'right') {
      const proposedWidth = Math.max(minW, gesture.origWidth + dayDelta * CONFIG.DAY_WIDTH);
      gesture.nextLeft = gesture.origLeft;
      gesture.nextWidth = proposedWidth;
      cardEl.style.width = `${proposedWidth}px`;
    } else if (gesture.mode === 'left') {
      const maxShrinkDays = Math.floor((gesture.origWidth - minW) / CONFIG.DAY_WIDTH);
      const actualDayDelta = clamp(dayDelta, -Number.MAX_SAFE_INTEGER, maxShrinkDays);
      const proposedLeft = clamp(gesture.origLeft + actualDayDelta * CONFIG.DAY_WIDTH, 0, Number.MAX_SAFE_INTEGER);
      const proposedWidth = Math.max(minW, gesture.origWidth - actualDayDelta * CONFIG.DAY_WIDTH);
      gesture.nextLeft = proposedLeft;
      gesture.nextWidth = proposedWidth;
      cardEl.style.transform = `translateX(${proposedLeft - gesture.origLeft}px)`;
      cardEl.style.width = `${proposedWidth}px`;
    }

    updateFloatingDateTip(cardEl, gesture);
  }

  function requestPreview() {
    if (rafId === null) rafId = requestAnimationFrame(applyPreview);
  }

  function commitCardPosition(leftPx, widthPxValue, { withTransition = false } = {}) {
    // ドロップ時のガタつき防止：一度transitionを切って、left/width/transformを同一フレームで確定する。
    cardEl.style.transition = 'none';
    cardEl.style.left = `${leftPx}px`;
    cardEl.style.width = `${widthPxValue}px`;
    cardEl.style.transform = '';
    cardEl.getBoundingClientRect(); // transition:none を確実に反映させる強制リフロー
    if (withTransition) {
      cardEl.classList.add('settling');
      cardEl.style.transition = '';
    } else {
      cardEl.style.transition = '';
    }
  }

  function startGesture(e) {
    if (schedule.locked || gesture.saving) return;
    const handle = e.target.dataset.handle;
    gesture.mode = handle === 'left' ? 'left' : handle === 'right' ? 'right' : 'move';
    gesture.pointerId = e.pointerId;
    gesture.startX = e.clientX;
    gesture.origLeft = parseFloat(cardEl.style.left || '0');
    gesture.origWidth = parseFloat(cardEl.style.width || `${CONFIG.DAY_WIDTH}`);
    gesture.rawDx = 0;
    gesture.dayDx = 0;
    gesture.nextLeft = gesture.origLeft;
    gesture.nextWidth = gesture.origWidth;
    gesture.started = false;

    state.activeGesture = gesture;
    cardEl.setPointerCapture(e.pointerId);
    cardEl.classList.add('dragging');
    cardEl.classList.remove('settling', 'card-shake', 'save-error', 'snapped');
    cardEl.style.cursor = gesture.mode === 'move' ? 'grabbing' : 'ew-resize';
    e.preventDefault();
  }

  function moveGesture(e) {
    if (!gesture.mode || gesture.pointerId !== e.pointerId) return;
    gesture.rawDx = e.clientX - gesture.startX;
    if (!gesture.started && Math.abs(gesture.rawDx) >= CONFIG.DRAG_START_THRESHOLD) {
      gesture.started = true;
      cardEl.classList.add('drag-active');
    }
    requestPreview();
    e.preventDefault();
  }

  function cancelGesture(e) {
    if (!gesture.mode || gesture.pointerId !== e.pointerId) return;
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    try { cardEl.releasePointerCapture?.(e.pointerId); } catch (_) {}

    // pointercancelは保存しない。元位置へ即時復帰して後始末だけ行う。
    commitCardPosition(gesture.origLeft, gesture.origWidth, { withTransition: false });
    cleanupGestureClasses();
    gesture.saving = false;
    resetGestureState();
  }

  async function endGesture(e) {
    if (!gesture.mode || gesture.pointerId !== e.pointerId) return;
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
      applyPreview();
    }

    try { cardEl.releasePointerCapture?.(e.pointerId); } catch (_) {}
    cardEl.classList.remove('dragging', 'drag-active');
    cardEl.style.cursor = 'grab';

    // クリックだけなら保存しない。無駄なPATCH/再描画とスマホ誤保存を防ぐ。
    if (!gesture.started) {
      commitCardPosition(gesture.origLeft, gesture.origWidth, { withTransition: false });
      cleanupGestureClasses();
      resetGestureState();
      return;
    }

    const finalLeft = Math.max(0, Math.round(gesture.nextLeft / CONFIG.DAY_WIDTH) * CONFIG.DAY_WIDTH);
    const finalWidth = Math.max(CONFIG.DAY_WIDTH, Math.round(gesture.nextWidth / CONFIG.DAY_WIDTH) * CONFIG.DAY_WIDTH);

    commitCardPosition(finalLeft, finalWidth, { withTransition: false });

    const startDay = Math.round(finalLeft / CONFIG.DAY_WIDTH);
    const durationDays = Math.max(1, Math.round(finalWidth / CONFIG.DAY_WIDTH));
    let nextStart = dateByOffset(startDay);
    let nextEnd = dateByOffset(startDay + durationDays - 1);

    try {
      gesture.saving = true;
      cardEl.classList.add('saving');

      const snapped = await trySnap(schedule, nextStart, nextEnd);
      if (snapped) {
        nextStart = snapped.start_date;
        nextEnd = snapped.end_date;
        const snappedLeft = offsetPx(nextStart);
        const snappedWidth = widthPx(nextStart, nextEnd);
        commitCardPosition(snappedLeft, snappedWidth, { withTransition: true });
        cardEl.classList.add('snapped');
      } else {
        commitCardPosition(finalLeft, finalWidth, { withTransition: true });
      }

      await saveSchedule(schedule.schedule_id, nextStart, nextEnd);
      await sleep(CONFIG.SETTLE_MS);
      await loadAndRender();
    } catch (err) {
      console.error(err);
      cardEl.classList.add('save-error');
      alert('スケジュール保存に失敗しました。画面を更新して再確認してください。');
    } finally {
      cleanupGestureClasses();
      gesture.saving = false;
      resetGestureState();
    }
  }

  cardEl.addEventListener('pointerdown', startGesture);
  cardEl.addEventListener('pointermove', moveGesture);
  cardEl.addEventListener('pointerup', endGesture);
  cardEl.addEventListener('pointercancel', cancelGesture);
}

function updateFloatingDateTip(cardEl, gesture) {
  let tip = cardEl.querySelector('.date-tip');
  if (!tip) {
    tip = document.createElement('span');
    tip.className = 'date-tip';
    cardEl.appendChild(tip);
  }
  const left = Math.max(0, Math.round(gesture.nextLeft / CONFIG.DAY_WIDTH) * CONFIG.DAY_WIDTH);
  const width = Math.max(CONFIG.DAY_WIDTH, Math.round(gesture.nextWidth / CONFIG.DAY_WIDTH) * CONFIG.DAY_WIDTH);
  const startDay = Math.round(left / CONFIG.DAY_WIDTH);
  const duration = Math.max(1, Math.round(width / CONFIG.DAY_WIDTH));
  tip.textContent = `${dateByOffset(startDay)} → ${dateByOffset(startDay + duration - 1)}`;
}

function removeFloatingDateTip(cardEl) {
  cardEl.querySelector('.date-tip')?.remove();
}

async function trySnap(schedule, startDate, endDate) {
  if (!state.snapEnabled) return null;
  const res = await fetch('/api/scheduler/snap', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      schedule_id: schedule.schedule_id,
      start_date: startDate,
      end_date: endDate,
    }),
  });
  if (!res.ok) {
    console.warn(`snap failed: ${res.status}`);
    return null;
  }
  const data = await res.json();
  return data.snapped ? data : null;
}

async function saveSchedule(id, startDate, endDate) {
  const res = await fetch(`/api/scheduler/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start_date: startDate, end_date: endDate }),
  });
  if (!res.ok) throw new Error(`save failed: ${res.status}`);
  return res.json();
}

function calcDailyLoad(processName) {
  const load = {};
  state.schedules
    .filter(s => s.process_name === processName)
    .forEach(s => {
      let d = parseDate(s.start_date);
      const e = parseDate(s.end_date);
      while (d <= e) {
        const key = fmtDate(d);
        load[key] = (load[key] || 0) + 1;
        d.setDate(d.getDate() + 1);
      }
    });
  return load;
}

function renderLoadWarnings() {
  let html = '<h6>負荷超過アラート</h6>';
  let found = false;
  [...new Set(state.schedules.map(s => s.process_name))].forEach(processName => {
    const load = calcDailyLoad(processName);
    Object.entries(load).forEach(([date, count]) => {
      if (count >= 2) {
        found = true;
        html += `<span class="badge text-bg-warning me-1">${processName} ${date}: ${count}件重複</span>`;
      }
    });
  });
  els.loadWarnings.innerHTML = found ? html : '<span class="text-muted">負荷超過アラートなし</span>';
}

async function applyQualityFlags(orderIds) {
  if (state.qualityAbort) state.qualityAbort.abort();
  state.qualityAbort = new AbortController();
  const signal = state.qualityAbort.signal;

  for (const orderId of orderIds) {
    try {
      const res = await fetch(`/api/scheduler/load/${orderId}`, { signal });
      const data = await res.json();
      if (data.has_issue) {
        document.querySelectorAll(`[data-order-id="${orderId}"] .proc-card`).forEach(card => {
          if (card.querySelector('.quality-flag')) return;
          const flag = document.createElement('span');
          flag.className = 'quality-flag';
          flag.textContent = '⚠';
          flag.title = data.issue_detail || '品質異常あり';
          card.appendChild(flag);
        });
      }
    } catch (err) {
      if (err.name !== 'AbortError') console.warn(err);
    }
  }
}

els.btnLoad.addEventListener('click', loadAndRender);
els.generateForm.addEventListener('submit', async e => {
  e.preventDefault();
  const id = els.orderSelect.value;
  if (!id) return;
  await fetch(`/api/scheduler/generate/${id}`, { method: 'POST' });
  await loadAndRender();
});
els.btnPdf.addEventListener('click', () => {
  const win = window.open(`/scheduler/print?${new URLSearchParams(state.filters)}`, '_blank');
  if (!win) {
    alert('ポップアップがブロックされました。このサイトのポップアップを許可してください。');
    return;
  }
  win.addEventListener('load', () => {
    if (typeof html2pdf === 'undefined') {
      win.print();
      return;
    }
    html2pdf()
      .from(win.document.body)
      .set({
        margin: 10,
        filename: `schedule_${fmtDate(new Date()).replaceAll('-', '')}.pdf`,
        html2canvas: { scale: 2 },
        jsPDF: { orientation: 'landscape', unit: 'mm', format: 'a3' },
      })
      .save()
      .then(() => win.close());
  });
});

window.addEventListener('beforeunload', () => {
  if (state.qualityAbort) state.qualityAbort.abort();
});

loadAndRender();
