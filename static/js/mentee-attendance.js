(() => {
  const urlTemplate = window.MENTEE_ATTENDANCE_URL || '';
  const attendanceModal = document.getElementById('attendance-modal');
  const cancelModal = document.getElementById('cancel-booking-modal');

  function sessionLabel(button) {
    return `Сессия с ${button.dataset.mentorName} · ${button.dataset.sessionDate}, ${button.dataset.sessionTime}`;
  }

  function formAction(bookingId) {
    return urlTemplate.replace('{id}', bookingId);
  }

  function updateBodyScrollLock() {
    const anyOpen = (attendanceModal && !attendanceModal.hidden)
      || (cancelModal && !cancelModal.hidden);
    document.body.classList.toggle('attendance-modal-open', anyOpen);
  }

  if (attendanceModal) {
    const attendanceForm = attendanceModal.querySelector('[data-attendance-form]');
    const decisionInput = attendanceModal.querySelector('[data-attendance-decision]');
    const attendanceText = attendanceModal.querySelector('[data-attendance-text]');
    const confirmBtn = attendanceModal.querySelector('[data-attendance-confirm]');
    const declineBtn = attendanceModal.querySelector('[data-attendance-decline]');

    function openAttendanceModal(button) {
      if (attendanceText) attendanceText.textContent = sessionLabel(button);
      if (attendanceForm) attendanceForm.action = formAction(button.dataset.bookingId);
      if (decisionInput) decisionInput.value = '';

      attendanceModal.hidden = false;
      attendanceModal.setAttribute('aria-hidden', 'false');
      updateBodyScrollLock();
      attendanceModal.querySelector('.attendance-modal__close')?.focus();
    }

    function closeAttendanceModal() {
      attendanceModal.hidden = true;
      attendanceModal.setAttribute('aria-hidden', 'true');
      if (decisionInput) decisionInput.value = '';
      updateBodyScrollLock();
    }

    document.querySelectorAll('[data-attendance-open]').forEach((button) => {
      button.addEventListener('click', () => openAttendanceModal(button));
    });

    attendanceModal.querySelectorAll('[data-attendance-close]').forEach((el) => {
      el.addEventListener('click', closeAttendanceModal);
    });

    confirmBtn?.addEventListener('click', () => {
      if (decisionInput) decisionInput.value = 'confirm';
    });

    declineBtn?.addEventListener('click', () => {
      if (decisionInput) decisionInput.value = 'decline';
    });
  }

  if (cancelModal) {
    const cancelForm = cancelModal.querySelector('[data-cancel-form]');
    const cancelText = cancelModal.querySelector('[data-cancel-text]');

    function openCancelModal(button) {
      if (cancelText) cancelText.textContent = sessionLabel(button);
      if (cancelForm) cancelForm.action = formAction(button.dataset.bookingId);

      cancelModal.hidden = false;
      cancelModal.setAttribute('aria-hidden', 'false');
      updateBodyScrollLock();
      cancelModal.querySelector('.attendance-modal__close')?.focus();
    }

    function closeCancelModal() {
      cancelModal.hidden = true;
      cancelModal.setAttribute('aria-hidden', 'true');
      updateBodyScrollLock();
    }

    document.querySelectorAll('[data-cancel-open]').forEach((button) => {
      button.addEventListener('click', () => openCancelModal(button));
    });

    cancelModal.querySelectorAll('[data-cancel-close]').forEach((el) => {
      el.addEventListener('click', closeCancelModal);
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (cancelModal && !cancelModal.hidden) {
      cancelModal.querySelector('[data-cancel-close]')?.click();
    } else if (attendanceModal && !attendanceModal.hidden) {
      attendanceModal.querySelector('[data-attendance-close]')?.click();
    }
  });

  function bindSessionsExpand(list, expandBtn, label) {
    if (!list || !expandBtn || !label) return;
    expandBtn.addEventListener('click', () => {
      const expanded = expandBtn.getAttribute('aria-expanded') === 'true';
      expandBtn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      label.textContent = expanded ? 'Посмотреть все' : 'Свернуть';
      list.classList.toggle('mentor-dashboard-sessions--collapsed', expanded);
    });
  }

  bindSessionsExpand(
    document.querySelector('[data-sessions-list]'),
    document.querySelector('[data-sessions-expand]'),
    document.querySelector('[data-sessions-expand-label]'),
  );
})();
