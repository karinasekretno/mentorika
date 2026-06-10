(() => {
  const strip = document.querySelector('[data-reviews-strip]');
  if (!strip) return;

  const viewport = strip.querySelector('[data-reviews-viewport]');
  const scrollBtn = strip.querySelector('[data-reviews-scroll]');
  const scrollFade = strip.querySelector('[data-reviews-fade]');
  const modal = document.getElementById('review-booking-modal');
  const modalText = modal?.querySelector('[data-review-text]');
  const modalStars = modal?.querySelector('[data-review-modal-stars]');
  const modalComment = modal?.querySelector('[data-review-comment]');
  const modalError = modal?.querySelector('[data-review-error]');
  const modalSubmit = modal?.querySelector('[data-review-submit]');
  const rateUrlTemplate = window.MENTEE_BOOKING_RATE_URL || '';
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

  let activeBookingId = null;
  let modalRating = 0;
  const SCROLL_STEP = 300;

  function buildRateUrl(bookingId) {
    return rateUrlTemplate.replace('{id}', String(bookingId));
  }

  function setStarHover(starsEl, value) {
    if (!starsEl || starsEl.classList.contains('chat-session-rating__stars--readonly')) return;
    starsEl.querySelectorAll('.chat-session-rating__star').forEach((star, index) => {
      star.classList.toggle('chat-session-rating__star--hover', index < value);
    });
  }

  function setStarSelection(starsEl, value) {
    if (!starsEl) return;
    starsEl.querySelectorAll('.chat-session-rating__star').forEach((star, index) => {
      const active = index < value;
      star.classList.toggle('chat-session-rating__star--filled', active);
      star.classList.toggle('chat-session-rating__star--hover', active);
      star.setAttribute('aria-checked', active ? 'true' : 'false');
    });
    starsEl.dataset.selectedRating = String(value);
  }

  function updateScrollArrow() {
    if (!viewport) return;
    const canScroll = viewport.scrollWidth > viewport.clientWidth + 4;
    const atEnd = viewport.scrollLeft + viewport.clientWidth >= viewport.scrollWidth - 4;
    const showControls = canScroll && !atEnd;
    if (scrollBtn) scrollBtn.hidden = !showControls;
    if (scrollFade) scrollFade.hidden = !showControls;
  }

  function removeReviewCard(bookingId) {
    const card = strip.querySelector(`[data-review-card][data-booking-id="${bookingId}"]`);
    card?.remove();
    if (!strip.querySelector('[data-review-card]')) {
      strip.closest('.mentee-reviews-section')?.remove();
    } else {
      updateScrollArrow();
    }
  }

  function initCardStars() {
    strip.querySelectorAll('.mentee-review-card__stars').forEach((starsEl) => {
      const rating = Number(starsEl.dataset.selectedRating || 0);
      if (rating > 0) setStarSelection(starsEl, rating);
    });
  }

  async function submitRating(bookingId, rating, text = '') {
    const formData = new FormData();
    if (rating) formData.append('rating', String(rating));
    if (text) formData.append('text', text);

    const response = await fetch(buildRateUrl(bookingId), {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: formData,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || 'Не удалось отправить оценку.');
    }
    return data;
  }

  function openReviewModal(button) {
    if (!modal) return;
    const card = button.closest('[data-review-card]');
    const existingRating = Number(card?.querySelector('[data-selected-rating]')?.dataset.selectedRating || 0);
    activeBookingId = button.dataset.bookingId;
    modalRating = existingRating;
    if (modalText) {
      modalText.textContent = `Сессия с ${button.dataset.mentorName}, ${button.dataset.sessionDate}, ${button.dataset.sessionTime}`;
    }
    if (modalComment) modalComment.value = '';
    if (modalError) {
      modalError.hidden = true;
      modalError.textContent = '';
    }
    setStarSelection(modalStars, modalRating);
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    modal.querySelector('.attendance-modal__close')?.focus();
  }

  function closeReviewModal() {
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    activeBookingId = null;
    modalRating = 0;
  }

  scrollBtn?.addEventListener('click', () => {
    viewport?.scrollBy({ left: SCROLL_STEP, behavior: 'smooth' });
  });

  viewport?.addEventListener('scroll', updateScrollArrow, { passive: true });
  window.addEventListener('resize', updateScrollArrow);

  strip.addEventListener('mouseover', (event) => {
    const star = event.target.closest('.mentee-review-card .chat-session-rating__star[data-rating]');
    if (!star || star.disabled) return;
    const starsEl = star.closest('.chat-session-rating__stars');
    setStarHover(starsEl, Number(star.dataset.rating));
  });

  strip.addEventListener('mouseout', (event) => {
    const starsEl = event.target.closest('.mentee-review-card .chat-session-rating__stars');
    if (!starsEl || starsEl.classList.contains('chat-session-rating__stars--readonly')) return;
    if (event.relatedTarget && starsEl.contains(event.relatedTarget)) return;
    const selected = Number(starsEl.dataset.selectedRating || 0);
    setStarHover(starsEl, selected);
  });

  strip.addEventListener('click', async (event) => {
    const openBtn = event.target.closest('[data-review-open]');
    if (openBtn) {
      openReviewModal(openBtn);
      return;
    }

    const star = event.target.closest('.mentee-review-card .chat-session-rating__star[data-rating]');
    if (!star || star.disabled) return;

    const card = star.closest('[data-review-card]');
    const bookingId = card?.dataset.bookingId;
    const rating = Number(star.dataset.rating);
    if (!bookingId || !rating) return;

    const starsEl = star.closest('.chat-session-rating__stars');
    card.querySelectorAll('.chat-session-rating__star').forEach((btn) => {
      btn.disabled = true;
    });

    try {
      const data = await submitRating(bookingId, rating);
      setStarSelection(starsEl, data.rating || rating);
      card.querySelectorAll('.chat-session-rating__star').forEach((btn) => {
        btn.disabled = false;
      });
      if (data.complete) {
        removeReviewCard(bookingId);
      }
    } catch (error) {
      card.querySelectorAll('.chat-session-rating__star').forEach((btn) => {
        btn.disabled = false;
      });
      window.alert(error.message || 'Не удалось отправить оценку.');
    }
  });

  modalStars?.addEventListener('mouseover', (event) => {
    const star = event.target.closest('[data-rating]');
    if (!star) return;
    setStarHover(modalStars, Number(star.dataset.rating));
  });

  modalStars?.addEventListener('mouseout', (event) => {
    if (event.relatedTarget && modalStars.contains(event.relatedTarget)) return;
    setStarHover(modalStars, modalRating);
  });

  modalStars?.addEventListener('click', (event) => {
    const star = event.target.closest('[data-rating]');
    if (!star) return;
    modalRating = Number(star.dataset.rating);
    setStarSelection(modalStars, modalRating);
    if (modalError) modalError.hidden = true;
  });

  modalSubmit?.addEventListener('click', async () => {
    if (!activeBookingId) return;
    const text = modalComment?.value?.trim() || '';
    if (modalRating < 1 || modalRating > 5) {
      if (modalError) {
        modalError.textContent = 'Выберите от 1 до 5 звёзд.';
        modalError.hidden = false;
      }
      return;
    }
    if (!text) {
      if (modalError) {
        modalError.textContent = 'Напишите отзыв или поставьте оценку звёздами на карточке.';
        modalError.hidden = false;
      }
      return;
    }
    modalSubmit.disabled = true;
    try {
      const data = await submitRating(activeBookingId, modalRating, text);
      const bookingId = activeBookingId;
      closeReviewModal();
      if (data.complete) {
        removeReviewCard(bookingId);
      }
    } catch (error) {
      if (modalError) {
        modalError.textContent = error.message || 'Не удалось отправить отзыв.';
        modalError.hidden = false;
      }
    } finally {
      modalSubmit.disabled = false;
    }
  });

  modal?.querySelectorAll('[data-review-close]').forEach((el) => {
    el.addEventListener('click', closeReviewModal);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal && !modal.hidden) {
      closeReviewModal();
    }
  });

  initCardStars();
  updateScrollArrow();
})();
