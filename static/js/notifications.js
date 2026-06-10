document.addEventListener('DOMContentLoaded', () => {
  const wrap = document.querySelector('[data-notifications]');
  if (!wrap) return;

  const bell = wrap.querySelector('[data-notifications-toggle]');
  const panel = wrap.querySelector('[data-notifications-panel]');
  const list = wrap.querySelector('[data-notifications-list]');
  const badge = wrap.querySelector('[data-notifications-badge]');
  const markAllBtn = wrap.querySelector('[data-notifications-mark-all]');

  let isOpen = false;
  let isLoading = false;

  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function setUnreadCount(count) {
    if (!badge) return;
    const value = Number(count) || 0;
    if (value > 0) {
      badge.hidden = false;
      badge.textContent = value > 99 ? '99+' : String(value);
    } else {
      badge.hidden = true;
      badge.textContent = '';
    }
  }

  function renderEmpty(text) {
    list.innerHTML = `<div class="notifications-panel__empty">${text}</div>`;
  }

  function renderNotifications(items) {
    if (!items.length) {
      renderEmpty('Пока нет уведомлений');
      return;
    }
    list.innerHTML = items.map(item => `
      <button
        type="button"
        class="notifications-item${item.is_read ? '' : ' notifications-item--unread'}"
        data-notification-id="${item.id}"
        data-notification-link="${item.link || ''}"
      >
        <span class="notifications-item__title">${escapeHtml(item.title)}</span>
        <span class="notifications-item__body">${escapeHtml(item.body)}</span>
        <span class="notifications-item__time">${escapeHtml(item.time_ago)}</span>
      </button>
    `).join('');
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
  }

  async function loadNotifications() {
    if (isLoading) return;
    isLoading = true;
    list.innerHTML = '<div class="notifications-panel__loading">Загрузка...</div>';
    try {
      const response = await fetch('/notifications/');
      if (!response.ok) throw new Error('load failed');
      const data = await response.json();
      setUnreadCount(data.unread_count);
      renderNotifications(data.notifications || []);
    } catch {
      renderEmpty('Не удалось загрузить уведомления');
    } finally {
      isLoading = false;
    }
  }

  async function markRead(notificationId) {
    const response = await fetch(`/notifications/${notificationId}/read/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() },
    });
    if (!response.ok) return null;
    return response.json();
  }

  async function markAllRead() {
    const response = await fetch('/notifications/read-all/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() },
    });
    if (!response.ok) return;
    const data = await response.json();
    setUnreadCount(data.unread_count);
    await loadNotifications();
  }

  function openPanel() {
    isOpen = true;
    panel.hidden = false;
    bell.setAttribute('aria-expanded', 'true');
    loadNotifications();
  }

  function closePanel() {
    isOpen = false;
    panel.hidden = true;
    bell.setAttribute('aria-expanded', 'false');
  }

  bell.addEventListener('click', e => {
    e.stopPropagation();
    if (isOpen) {
      closePanel();
    } else {
      openPanel();
    }
  });

  markAllBtn?.addEventListener('click', async e => {
    e.preventDefault();
    await markAllRead();
  });

  list.addEventListener('click', async e => {
    const item = e.target.closest('[data-notification-id]');
    if (!item) return;
    const notificationId = item.dataset.notificationId;
    const link = item.dataset.notificationLink;
    const data = await markRead(notificationId);
    if (data) setUnreadCount(data.unread_count);
    item.classList.remove('notifications-item--unread');
    if (link) {
      window.location.href = link;
    }
  });

  document.addEventListener('click', e => {
    if (!isOpen) return;
    if (!wrap.contains(e.target)) closePanel();
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && isOpen) closePanel();
  });

  setInterval(() => {
    if (!document.hidden) {
      fetch('/notifications/')
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data) setUnreadCount(data.unread_count);
        })
        .catch(() => {});
    }
  }, 60000);
});
