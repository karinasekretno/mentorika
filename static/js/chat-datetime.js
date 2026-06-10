(() => {
  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function parseDate(iso) {
    if (!iso) return null;
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function formatMessageTime(iso) {
    const date = parseDate(iso);
    if (!date) return '';
    return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function formatListTime(iso) {
    const date = parseDate(iso);
    if (!date) return '';
    return `${pad(date.getDate())}.${pad(date.getMonth() + 1)} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function applyLocalTimes(root = document) {
    root.querySelectorAll('.chat-message__time[datetime]').forEach((el) => {
      const formatted = formatMessageTime(el.getAttribute('datetime'));
      if (formatted) el.textContent = formatted;
    });
    root.querySelectorAll('.chat-list__time[data-datetime]').forEach((el) => {
      const formatted = formatListTime(el.dataset.datetime);
      if (formatted) el.textContent = formatted;
    });
  }

  window.ChatDateTime = {
    formatMessageTime,
    formatListTime,
    applyLocalTimes,
  };
})();
