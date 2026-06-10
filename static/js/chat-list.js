(() => {
  const searchInput = document.querySelector('[data-chat-search]');
  const list = document.querySelector('[data-chat-list]');
  const emptyState = document.querySelector('[data-chat-search-empty]');
  if (!searchInput || !list) return;

  const items = [...list.querySelectorAll('[data-chat-item]')];

  function filterChats() {
    const query = searchInput.value.trim().toLowerCase();
    let visibleCount = 0;

    items.forEach((item) => {
      const link = item.querySelector('[data-search-name]');
      const name = (link?.dataset.searchName || '').toLowerCase();
      const matches = !query || name.includes(query);
      item.hidden = !matches;
      if (matches) visibleCount += 1;
    });

    if (emptyState) {
      emptyState.hidden = visibleCount > 0 || !query;
    }
  }

  searchInput.addEventListener('input', filterChats);
  searchInput.addEventListener('search', filterChats);
  window.ChatDateTime?.applyLocalTimes();
})();
