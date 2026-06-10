(() => {
  const layout = document.querySelector('[data-chat-layout]');
  if (!layout) return;

  const sharedUrl = layout.dataset.sharedUrl;
  const toggleBtn = layout.querySelector('[data-chat-shared-toggle]');
  const panel = layout.querySelector('[data-chat-shared-panel]');
  const tabs = layout.querySelectorAll('[data-shared-tab]');
  const groupsEl = layout.querySelector('[data-chat-shared-groups]');
  const emptyEl = layout.querySelector('[data-chat-shared-empty]');

  let activeTab = 'images';
  let isOpen = false;
  let loading = false;
  let cache = {};

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setOpen(open) {
    isOpen = open;
    if (panel) panel.hidden = !open;
    if (toggleBtn) {
      toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggleBtn.classList.toggle('chat-layout__shared-toggle--active', open);
    }
    layout.classList.toggle('chat-layout--shared-open', open);
    if (open) {
      loadTab(activeTab);
    }
  }

  function setActiveTab(tab) {
    activeTab = tab;
    tabs.forEach((button) => {
      const isActive = button.dataset.sharedTab === tab;
      button.classList.toggle('chat-shared-tab--active', isActive);
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
  }

  function groupItems(items) {
    const groups = new Map();
    items.forEach((item) => {
      const key = item.month_key || 'unknown';
      if (!groups.has(key)) {
        groups.set(key, { label: item.month_label || '', items: [] });
      }
      groups.get(key).items.push(item);
    });
    return [...groups.values()];
  }

  function renderImageItem(item) {
    return `
      <a href="${escapeHtml(item.url)}" class="chat-shared-item chat-shared-item--image" target="_blank" rel="noopener" title="${escapeHtml(item.name)}">
        <img src="${escapeHtml(item.url)}" alt="${escapeHtml(item.name)}" loading="lazy">
      </a>
    `;
  }

  function renderFileItem(item) {
    return `
      <a href="${escapeHtml(item.url)}" class="chat-shared-item chat-shared-item--file" target="_blank" rel="noopener">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
        <span>${escapeHtml(item.name)}</span>
      </a>
    `;
  }

  function renderLinkItem(item) {
    return `
      <a href="${escapeHtml(item.url)}" class="chat-shared-item chat-shared-item--link" target="_blank" rel="noopener">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
        <span>${escapeHtml(item.name)}</span>
      </a>
    `;
  }

  function renderGroup(group, tab) {
    const renderItem = tab === 'images'
      ? renderImageItem
      : tab === 'files'
        ? renderFileItem
        : renderLinkItem;
    const gridClass = tab === 'images' ? 'chat-shared-panel__grid' : 'chat-shared-panel__list';
    return `
      <section class="chat-shared-panel__group">
        <h3 class="chat-shared-panel__month">${escapeHtml(group.label)}</h3>
        <div class="${gridClass}">
          ${group.items.map(renderItem).join('')}
        </div>
      </section>
    `;
  }

  function renderItems(items, tab) {
    if (!groupsEl || !emptyEl) return;
    if (!items.length) {
      groupsEl.innerHTML = '';
      emptyEl.hidden = false;
      return;
    }
    emptyEl.hidden = true;
    const groups = groupItems(items);
    groupsEl.innerHTML = groups.map((group) => renderGroup(group, tab)).join('');
  }

  async function loadTab(tab) {
    if (!sharedUrl || loading) return;
    if (cache[tab]) {
      renderItems(cache[tab], tab);
      return;
    }
    loading = true;
    if (groupsEl) groupsEl.innerHTML = '<p class="chat-shared-panel__loading">Загрузка…</p>';
    if (emptyEl) emptyEl.hidden = true;
    try {
      const res = await fetch(`${sharedUrl}?type=${encodeURIComponent(tab)}`, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Ошибка загрузки');
      cache[tab] = data.items || [];
      renderItems(cache[tab], tab);
    } catch {
      if (groupsEl) {
        groupsEl.innerHTML = '<p class="chat-shared-panel__error">Не удалось загрузить вложения.</p>';
      }
    } finally {
      loading = false;
    }
  }

  toggleBtn?.addEventListener('click', () => {
    setOpen(!isOpen);
  });

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const nextTab = tab.dataset.sharedTab;
      if (!nextTab || nextTab === activeTab) return;
      setActiveTab(nextTab);
      loadTab(nextTab);
    });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isOpen) {
      setOpen(false);
    }
  });
})();
