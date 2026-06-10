(() => {
  const root = document.querySelector('[data-schedule-calendar]');
  if (!root || !window.MENTOR_SCHEDULE) return;

  const { slotsUrl, editSlotUrl, deleteSlotUrl, csrfToken } = window.MENTOR_SCHEDULE;

  const grid = root.querySelector('[data-cal-grid]');
  const monthLabel = root.querySelector('[data-cal-month-label]');
  const prevBtn = root.querySelector('[data-cal-prev]');
  const nextBtn = root.querySelector('[data-cal-next]');
  const daySlots = document.querySelector('[data-schedule-day-slots]');
  const dayLabel = document.querySelector('[data-schedule-day-label]');
  const dayList = document.querySelector('[data-schedule-day-list]');
  const dayEmpty = document.querySelector('[data-schedule-day-empty]');
  const addSlotBtn = document.querySelector('[data-schedule-add-slot]');
  const slotForm = document.querySelector('.slot-form');
  const slotDateInput = slotForm?.querySelector('[name="date"]');
  const editModal = document.getElementById('edit-slot-modal');
  const editForm = editModal?.querySelector('[data-slot-edit-form]');
  const editDateInput = editModal?.querySelector('[data-slot-edit-date]');
  const editStartInput = editModal?.querySelector('[data-slot-edit-start]');
  const editEndInput = editModal?.querySelector('[data-slot-edit-end]');

  const MONTH_NAMES = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
  ];

  const PENCIL_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>';
  const DELETE_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M18 6L6 18M6 6l12 12"/></svg>';

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  let viewYear = today.getFullYear();
  let viewMonth = today.getMonth();
  let availableDates = new Set();
  let selectedDate = null;

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

  function formatShortDisplayDate(iso) {
    const date = parseIso(iso);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'numeric',
      year: 'numeric',
    });
  }

  function formatSessionDatetime(iso, start, end) {
    const date = parseIso(iso);
    const datePart = date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
    return `${datePart}, ${start}–${end}`;
  }

  function updateBodyScrollLock() {
    const open = editModal && !editModal.hidden;
    document.body.classList.toggle('attendance-modal-open', open);
  }

  function openEditModal(slot) {
    if (!editModal || !editForm) return;
    editForm.action = editSlotUrl(slot.id);
    if (editDateInput) editDateInput.value = slot.date;
    if (editStartInput) editStartInput.value = slot.start;
    if (editEndInput) editEndInput.value = slot.end;
    editModal.hidden = false;
    editModal.setAttribute('aria-hidden', 'false');
    updateBodyScrollLock();
    editDateInput?.focus();
  }

  function closeEditModal() {
    if (!editModal) return;
    editModal.hidden = true;
    editModal.setAttribute('aria-hidden', 'true');
    updateBodyScrollLock();
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
      const isClickable = !outside && !isPast;
      const hasSlots = isClickable && availableDates.has(iso);
      const isSelected = selectedDate === iso;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'booking-calendar__day';
      btn.textContent = String(dayNum);
      btn.dataset.date = iso;

      if (outside) btn.classList.add('booking-calendar__day--outside');
      if (isPast && !outside) btn.classList.add('booking-calendar__day--past');
      if (hasSlots) btn.classList.add('booking-calendar__day--available');
      if (isSelected) btn.classList.add('booking-calendar__day--selected');
      if (isSameDay(cellDate, today)) btn.classList.add('booking-calendar__day--today');

      btn.disabled = !isClickable;
      btn.setAttribute('aria-label', formatDisplayDate(iso));
      if (isClickable) {
        btn.addEventListener('click', () => selectDate(iso));
      }

      grid.appendChild(btn);
    }
  }

  function renderSlotActions(slot) {
    const actions = document.createElement('div');
    actions.className = 'mentor-dashboard-session__action-icons';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'mentor-dashboard-session__action-icon';
    editBtn.setAttribute('aria-label', 'Изменить слот');
    editBtn.dataset.slotEdit = '';
    editBtn.dataset.slotId = String(slot.id);
    editBtn.dataset.slotDate = slot.date;
    editBtn.dataset.slotStart = slot.start;
    editBtn.dataset.slotEnd = slot.end;
    editBtn.innerHTML = PENCIL_ICON;
    actions.appendChild(editBtn);

    const form = document.createElement('form');
    form.method = 'post';
    form.action = deleteSlotUrl(slot.id);
    form.className = 'schedule-slot__delete-form';

    const csrf = document.createElement('input');
    csrf.type = 'hidden';
    csrf.name = 'csrfmiddlewaretoken';
    csrf.value = csrfToken;
    form.appendChild(csrf);

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'submit';
    deleteBtn.className = 'mentor-dashboard-session__action-icon';
    deleteBtn.setAttribute('aria-label', 'Удалить слот');
    deleteBtn.innerHTML = DELETE_ICON;
    form.appendChild(deleteBtn);
    actions.appendChild(form);

    return actions;
  }

  function renderBookedSlotActions(slot) {
    const actions = document.createElement('div');
    actions.className = 'mentor-dashboard-session__action-icons';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'mentor-dashboard-session__action-icon';
    editBtn.setAttribute('aria-label', 'Изменить время');
    editBtn.setAttribute('data-reschedule-open', '');
    editBtn.dataset.bookingId = String(slot.booking_id);
    editBtn.dataset.menteeName = slot.mentee || 'учеником';
    editBtn.dataset.sessionDate = slot.date;
    editBtn.dataset.sessionStart = slot.start;
    editBtn.dataset.sessionEnd = slot.end;
    editBtn.innerHTML = PENCIL_ICON;
    actions.appendChild(editBtn);

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'mentor-dashboard-session__action-icon';
    cancelBtn.setAttribute('aria-label', 'Отменить запись');
    cancelBtn.setAttribute('data-mentor-cancel-open', '');
    cancelBtn.dataset.bookingId = String(slot.booking_id);
    cancelBtn.dataset.menteeName = slot.mentee || 'учеником';
    cancelBtn.dataset.sessionDate = formatShortDisplayDate(slot.date);
    cancelBtn.dataset.sessionTime = `${slot.start}–${slot.end}`;
    cancelBtn.innerHTML = DELETE_ICON;
    actions.appendChild(cancelBtn);

    return actions;
  }

  function renderSlotItem(slot) {
    const item = document.createElement('li');
    item.className = 'mentor-dashboard-session';

    const main = document.createElement('div');
    main.className = 'mentor-dashboard-session__main';

    const name = document.createElement('p');
    name.className = 'mentor-dashboard-session__name';
    name.textContent = slot.booked
      ? (slot.mentee || 'Запись')
      : 'Свободный слот';

    const datetime = document.createElement('p');
    datetime.className = 'mentor-dashboard-session__datetime';
    datetime.textContent = formatSessionDatetime(slot.date, slot.start, slot.end);

    main.appendChild(name);
    main.appendChild(datetime);

    const aside = document.createElement('div');
    aside.className = 'mentor-dashboard-session__aside';

    const actions = document.createElement('div');
    actions.className = 'mentor-dashboard-session__actions mentor-dashboard-session__actions--mentor';

    const status = document.createElement('span');
    if (slot.booked) {
      if (slot.session_state === 'started') {
        status.className = 'mentor-dashboard-session__status mentor-dashboard-session__status--started';
        status.textContent = 'Сессия началась';
      } else {
        status.className = 'mentor-dashboard-session__status mentor-dashboard-session__status--booked';
        status.textContent = 'Забронирован';
      }
    } else {
      status.className = 'mentor-dashboard-session__status mentor-dashboard-session__status--completed';
      status.textContent = 'Свободен';
    }

    actions.appendChild(status);
    if (slot.booked && slot.can_manage) {
      actions.appendChild(renderBookedSlotActions(slot));
    } else if (!slot.booked) {
      actions.appendChild(renderSlotActions(slot));
    }

    aside.appendChild(actions);
    item.appendChild(main);
    item.appendChild(aside);
    return item;
  }

  async function selectDate(iso) {
    selectedDate = iso;
    renderCalendar();

    daySlots.hidden = false;
    dayLabel.textContent = formatDisplayDate(iso);
    dayList.hidden = false;
    dayEmpty.hidden = true;
    dayList.innerHTML = '<li class="mentor-dashboard-session"><p class="booking-slots__loading">Загрузка…</p></li>';

    const slots = await fetchSlots(iso);
    dayList.innerHTML = '';

    if (!slots.length) {
      dayList.hidden = true;
      dayEmpty.hidden = false;
      return;
    }

    dayList.hidden = false;
    dayEmpty.hidden = true;
    slots.forEach((slot) => {
      dayList.appendChild(renderSlotItem({
        ...slot,
        date: slot.date || iso,
      }));
    });
  }

  function resetDaySlots() {
    selectedDate = null;
    daySlots.hidden = true;
    dayList.innerHTML = '';
    dayList.hidden = false;
    dayEmpty.hidden = true;
  }

  async function loadMonth() {
    availableDates = await fetchAvailableDates(viewYear, viewMonth);
    renderCalendar();
  }

  addSlotBtn?.addEventListener('click', () => {
    if (!selectedDate || !slotDateInput) return;
    slotDateInput.value = selectedDate;
    document.getElementById('slot-add-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    slotForm?.querySelector('[name="start_time"]')?.focus();
  });

  dayList?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-slot-edit]');
    if (!button) return;
    openEditModal({
      id: button.dataset.slotId,
      date: button.dataset.slotDate,
      start: button.dataset.slotStart,
      end: button.dataset.slotEnd,
    });
  });

  editModal?.querySelectorAll('[data-slot-edit-close]').forEach((el) => {
    el.addEventListener('click', closeEditModal);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && editModal && !editModal.hidden) {
      closeEditModal();
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

  loadMonth();
})();
