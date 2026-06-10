(() => {
  const panel = document.getElementById('booking-panel');
  if (!panel || !window.MENTOR_BOOKING) return;

  const { slotsUrl } = window.MENTOR_BOOKING;
  const openBtn = document.querySelector('[data-booking-open]');
  const panelTitle = panel.querySelector('#booking-panel-title');
  const selectStep = panel.querySelector('[data-booking-select]');
  const confirmStep = panel.querySelector('[data-booking-confirm]');
  const backBtn = panel.querySelector('[data-booking-back]');
  const continueBtn = panel.querySelector('[data-booking-continue]');
  const grid = panel.querySelector('[data-cal-grid]');
  const monthLabel = panel.querySelector('[data-cal-month-label]');
  const prevBtn = panel.querySelector('[data-cal-prev]');
  const nextBtn = panel.querySelector('[data-cal-next]');
  const slotsContent = panel.querySelector('[data-slots-content]');
  const slotsDate = panel.querySelector('[data-slots-date]');
  const slotsList = panel.querySelector('[data-slots-list]');
  const slotsEmpty = panel.querySelector('[data-slots-empty]');
  const slotInput = panel.querySelector('[data-slot-input]');
  const confirmDate = panel.querySelector('[data-confirm-date]');
  const confirmTime = panel.querySelector('[data-confirm-time]');

  const MONTH_NAMES = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
  ];

  const WEEKDAY_NAMES = [
    'воскресенье', 'понедельник', 'вторник', 'среда',
    'четверг', 'пятница', 'суббота',
  ];

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  let viewYear = today.getFullYear();
  let viewMonth = today.getMonth();
  let availableDates = new Set();
  let selectedDate = null;
  let selectedSlot = null;

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function toIso(y, m, d) {
    return `${y}-${pad(m + 1)}-${pad(d)}`;
  }

  function parseIso(str) {
    const [y, m, d] = str.split('-').map(Number);
    return new Date(y, m - 1, d);
  }

  function monthKey(y, m) {
    return `${y}-${pad(m + 1)}`;
  }

  function formatDisplayDate(iso) {
    const date = parseIso(iso);
    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function formatConfirmDate(iso) {
    const date = parseIso(iso);
    const weekday = WEEKDAY_NAMES[date.getDay()];
    const day = date.getDate();
    const month = MONTH_NAMES[date.getMonth()].toLowerCase();
    const year = date.getFullYear();
    return `${weekday}, ${day} ${month} ${year}`;
  }

  async function fetchAvailableDates(y, m) {
    const res = await fetch(`${slotsUrl}?month=${monthKey(y, m)}`);
    if (!res.ok) return new Set();
    const data = await res.json();
    return new Set(data.dates || []);
  }

  async function fetchSlots(iso) {
    const res = await fetch(`${slotsUrl}?date=${iso}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.slots || [];
  }

  function isSameDay(a, b) {
    return a.getFullYear() === b.getFullYear()
      && a.getMonth() === b.getMonth()
      && a.getDate() === b.getDate();
  }

  function clearSlotSelection() {
    selectedSlot = null;
    if (slotInput) slotInput.value = '';
    if (continueBtn) continueBtn.disabled = true;
    slotsList.querySelectorAll('input[type="radio"]').forEach((input) => {
      input.checked = false;
    });
  }

  function showSelectStep() {
    selectStep.hidden = false;
    confirmStep.hidden = true;
    if (panelTitle) panelTitle.textContent = 'Запись на сессию';
  }

  function showConfirmStep() {
    if (!selectedSlot || !selectedDate) return;

    if (confirmDate) confirmDate.textContent = formatConfirmDate(selectedDate);
    if (confirmTime) confirmTime.textContent = `${selectedSlot.start} – ${selectedSlot.end}`;
    if (slotInput) slotInput.value = selectedSlot.id;

    selectStep.hidden = true;
    confirmStep.hidden = false;
    if (panelTitle) panelTitle.textContent = 'Подтверждение записи';
    backBtn?.focus();
  }

  function renderCalendar() {
    monthLabel.textContent = `${MONTH_NAMES[viewMonth]} ${viewYear}`;
    grid.innerHTML = '';

    const first = new Date(viewYear, viewMonth, 1);
    const startOffset = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const prevMonthDays = new Date(viewYear, viewMonth, 0).getDate();
    const totalCells = Math.ceil((startOffset + daysInMonth) / 7) * 7;

    for (let i = 0; i < totalCells; i += 1) {
      let dayNum;
      let cellYear = viewYear;
      let cellMonth = viewMonth;
      let outside = false;

      if (i < startOffset) {
        dayNum = prevMonthDays - startOffset + i + 1;
        cellMonth -= 1;
        if (cellMonth < 0) {
          cellMonth = 11;
          cellYear -= 1;
        }
        outside = true;
      } else if (i >= startOffset + daysInMonth) {
        dayNum = i - startOffset - daysInMonth + 1;
        cellMonth += 1;
        if (cellMonth > 11) {
          cellMonth = 0;
          cellYear += 1;
        }
        outside = true;
      } else {
        dayNum = i - startOffset + 1;
      }

      const iso = toIso(cellYear, cellMonth, dayNum);
      const cellDate = parseIso(iso);
      const isPast = cellDate < today;
      const isAvailable = !outside && !isPast && availableDates.has(iso);
      const isSelected = selectedDate === iso;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'booking-calendar__day';
      btn.textContent = String(dayNum);
      btn.dataset.date = iso;

      if (outside) btn.classList.add('booking-calendar__day--outside');
      if (isPast && !outside) btn.classList.add('booking-calendar__day--past');
      if (isAvailable) btn.classList.add('booking-calendar__day--available');
      if (isSelected) btn.classList.add('booking-calendar__day--selected');
      if (isSameDay(cellDate, today)) btn.classList.add('booking-calendar__day--today');

      btn.disabled = !isAvailable;
      btn.setAttribute('aria-label', formatDisplayDate(iso));
      if (isAvailable) {
        btn.addEventListener('click', () => selectDate(iso));
      }

      grid.appendChild(btn);
    }
  }

  function resetSlots() {
    selectedDate = null;
    selectedSlot = null;
    slotsContent.hidden = true;
    slotsList.innerHTML = '';
    slotsEmpty.hidden = true;
    if (continueBtn) continueBtn.disabled = true;
    if (slotInput) slotInput.value = '';
    showSelectStep();
  }

  function applySlotSelection(slot) {
    selectedSlot = { id: slot.id, start: slot.start, end: slot.end };
    if (continueBtn) continueBtn.disabled = false;
  }

  async function selectDate(iso, preselectedSlotId = null) {
    selectedDate = iso;
    clearSlotSelection();
    renderCalendar();

    slotsContent.hidden = false;
    slotsDate.textContent = formatDisplayDate(iso);
    slotsList.innerHTML = '<p class="booking-slots__loading">Загрузка…</p>';
    slotsEmpty.hidden = true;

    const slots = await fetchSlots(iso);
    slotsList.innerHTML = '';

    if (!slots.length) {
      slotsEmpty.hidden = false;
      return [];
    }

    let preselectedSlot = null;

    slots.forEach((slot) => {
      const label = document.createElement('label');
      label.className = 'booking-slots__item';
      label.innerHTML = `
        <input type="radio" name="booking_slot_pick" value="${slot.id}">
        <span class="booking-slots__item-body">
          <span class="booking-slots__time">${slot.start} – ${slot.end}</span>
          <span class="booking-slots__meta">1 сессия</span>
        </span>
      `;
      const radio = label.querySelector('input');
      radio.addEventListener('change', () => {
        applySlotSelection(slot);
      });
      if (preselectedSlotId && String(slot.id) === String(preselectedSlotId)) {
        radio.checked = true;
        preselectedSlot = slot;
        applySlotSelection(slot);
      }
      slotsList.appendChild(label);
    });

    return preselectedSlot ? [preselectedSlot] : slots;
  }

  async function loadMonth() {
    availableDates = await fetchAvailableDates(viewYear, viewMonth);
    renderCalendar();
    if (selectedDate && !availableDates.has(selectedDate)) {
      resetSlots();
    }
  }

  function revealPanel() {
    panel.hidden = false;
    panel.setAttribute('aria-hidden', 'false');
    document.body.classList.add('booking-panel-open');
  }

  function openPanel() {
    revealPanel();
    viewYear = today.getFullYear();
    viewMonth = today.getMonth();
    resetSlots();
    loadMonth();
    panel.querySelector('.booking-panel__close')?.focus();
  }

  async function openPanelWithPreset(dateIso, slotId) {
    revealPanel();
    showSelectStep();

    const presetDate = parseIso(dateIso);
    viewYear = presetDate.getFullYear();
    viewMonth = presetDate.getMonth();
    selectedDate = null;
    selectedSlot = null;
    slotsContent.hidden = true;
    slotsList.innerHTML = '';
    slotsEmpty.hidden = true;
    if (continueBtn) continueBtn.disabled = true;
    if (slotInput) slotInput.value = '';

    availableDates = await fetchAvailableDates(viewYear, viewMonth);
    renderCalendar();
    const matched = await selectDate(dateIso, slotId);

    if (matched && matched.length && selectedSlot) {
      showConfirmStep();
    } else {
      panel.querySelector('.booking-panel__close')?.focus();
    }
  }

  function clearBookingQueryParams() {
    const params = new URLSearchParams(window.location.search);
    if (!params.has('slot') && !params.has('date')) return;
    params.delete('slot');
    params.delete('date');
    const query = params.toString();
    const nextUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
    window.history.replaceState({}, '', nextUrl);
  }

  function closePanel() {
    panel.hidden = true;
    panel.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('booking-panel-open');
    resetSlots();
    openBtn?.focus();
  }

  openBtn?.addEventListener('click', openPanel);
  continueBtn?.addEventListener('click', showConfirmStep);
  backBtn?.addEventListener('click', showSelectStep);

  panel.querySelectorAll('[data-booking-close]').forEach((el) => {
    el.addEventListener('click', closePanel);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !panel.hidden) {
      if (!confirmStep.hidden) {
        showSelectStep();
      } else {
        closePanel();
      }
    }
  });

  prevBtn?.addEventListener('click', () => {
    viewMonth -= 1;
    if (viewMonth < 0) {
      viewMonth = 11;
      viewYear -= 1;
    }
    loadMonth();
  });

  nextBtn?.addEventListener('click', () => {
    viewMonth += 1;
    if (viewMonth > 11) {
      viewMonth = 0;
      viewYear += 1;
    }
    loadMonth();
  });

  const initialParams = new URLSearchParams(window.location.search);
  const presetSlotId = initialParams.get('slot');
  const presetDate = initialParams.get('date');
  if (presetSlotId && presetDate && /^\d{4}-\d{2}-\d{2}$/.test(presetDate)) {
    openPanelWithPreset(presetDate, presetSlotId).finally(clearBookingQueryParams);
  }
})();
