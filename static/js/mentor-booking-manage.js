(() => {
  const urlTemplate = window.MENTOR_BOOKING_MANAGE_URL || '';
  const rescheduleModal = document.getElementById('reschedule-booking-modal');
  const cancelModal = document.getElementById('mentor-cancel-booking-modal');

  function formAction(bookingId) {
    return urlTemplate.replace('{id}', bookingId);
  }

  function updateBodyScrollLock() {
    const anyOpen = (rescheduleModal && !rescheduleModal.hidden)
      || (cancelModal && !cancelModal.hidden);
    document.body.classList.toggle('attendance-modal-open', anyOpen);
  }

  if (rescheduleModal) {
    const rescheduleForm = rescheduleModal.querySelector('[data-reschedule-form]');
    const rescheduleText = rescheduleModal.querySelector('[data-reschedule-text]');
    const dateInput = rescheduleModal.querySelector('[data-reschedule-date]');
    const startInput = rescheduleModal.querySelector('[data-reschedule-start]');
    const endInput = rescheduleModal.querySelector('[data-reschedule-end]');

    function openRescheduleModal(button) {
      const menteeName = button.dataset.menteeName;
      if (rescheduleText) {
        rescheduleText.textContent = `Сессия с ${menteeName}`;
      }
      if (rescheduleForm) rescheduleForm.action = formAction(button.dataset.bookingId);
      if (dateInput) dateInput.value = button.dataset.sessionDate || '';
      if (startInput) startInput.value = button.dataset.sessionStart || '';
      if (endInput) endInput.value = button.dataset.sessionEnd || '';

      rescheduleModal.hidden = false;
      rescheduleModal.setAttribute('aria-hidden', 'false');
      updateBodyScrollLock();
      dateInput?.focus();
    }

    function closeRescheduleModal() {
      rescheduleModal.hidden = true;
      rescheduleModal.setAttribute('aria-hidden', 'true');
      updateBodyScrollLock();
    }

    document.addEventListener('click', (event) => {
      const button = event.target.closest('[data-reschedule-open]');
      if (button) openRescheduleModal(button);
    });

    rescheduleModal.querySelectorAll('[data-reschedule-close]').forEach((el) => {
      el.addEventListener('click', closeRescheduleModal);
    });
  }

  if (cancelModal) {
    const cancelForm = cancelModal.querySelector('[data-mentor-cancel-form]');
    const cancelText = cancelModal.querySelector('[data-mentor-cancel-text]');

    function sessionLabel(button) {
      return `Сессия с ${button.dataset.menteeName} · ${button.dataset.sessionDate}, ${button.dataset.sessionTime}`;
    }

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

    document.addEventListener('click', (event) => {
      const button = event.target.closest('[data-mentor-cancel-open]');
      if (button) openCancelModal(button);
    });

    cancelModal.querySelectorAll('[data-mentor-cancel-close]').forEach((el) => {
      el.addEventListener('click', closeCancelModal);
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (cancelModal && !cancelModal.hidden) {
      cancelModal.querySelector('[data-mentor-cancel-close]')?.click();
    } else if (rescheduleModal && !rescheduleModal.hidden) {
      rescheduleModal.querySelector('[data-reschedule-close]')?.click();
    }
  });
})();
