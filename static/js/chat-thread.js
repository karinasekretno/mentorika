(() => {
  const thread = document.querySelector('[data-chat-thread]');
  if (!thread) return;

  const messagesUrl = thread.dataset.messagesUrl;
  const messagesEl = thread.querySelector('[data-chat-messages]');
  const form = thread.querySelector('[data-chat-form]');
  const input = thread.querySelector('[data-chat-input]');
  const fileInput = thread.querySelector('[data-chat-file]');
  const attachBtn = thread.querySelector('[data-chat-attach]');
  const sendBtn = thread.querySelector('[data-chat-send]');
  const errorEl = thread.querySelector('[data-chat-error]');
  const previewList = thread.querySelector('[data-chat-preview-list]');
  const contextMenu = thread.querySelector('[data-chat-context-menu]');
  const deleteModal = thread.querySelector('[data-chat-delete-modal]');
  const deleteConfirmBtn = thread.querySelector('[data-chat-delete-confirm]');
  const replyPreview = thread.querySelector('[data-chat-reply-preview]');
  const replyLabel = thread.querySelector('[data-chat-reply-label]');
  const replyText = thread.querySelector('[data-chat-reply-text]');
  const replyCancelBtn = thread.querySelector('[data-chat-reply-cancel]');
  const emojiToggleBtn = thread.querySelector('[data-chat-emoji-toggle]');
  const emojiPicker = thread.querySelector('[data-chat-emoji-picker]');
  const emojiGrid = thread.querySelector('[data-chat-emoji-grid]');
  const csrfToken = form?.querySelector('[name=csrfmiddlewaretoken]')?.value;

  const CHAT_EMOJIS = [
    '😀', '😃', '😄', '😁', '😅', '😂', '🤣', '😊', '😇', '🙂', '🙃', '😉', '😌', '😍', '🥰', '😘',
    '😋', '😛', '😜', '🤪', '😝', '🤗', '🤭', '🤔', '🤐', '😐', '😑', '😶', '😏', '😒', '🙄', '😬',
    '😔', '😪', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🥳', '😎', '🤓', '😤', '😠', '😡', '🥺', '😢',
    '😭', '😱', '😳', '🤯', '😇', '👍', '👎', '👌', '✌️', '🤞', '🤟', '🤘', '👋', '🙌', '👏', '🙏',
    '💪', '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '💔', '💕', '💖', '💗', '💘', '💯', '✨', '⭐',
    '🔥', '🎉', '🎊', '✅', '❌', '❗', '❓', '💡', '📎', '📌', '✏️', '📝', '💬', '👀', '🙈', '🙉',
  ];

  let lastMessageId = Number(thread.dataset.lastMessageId || 0);
  let pendingFiles = [];
  let pollTimer = null;
  let sending = false;
  let replyTo = null;
  let contextMessage = null;
  let pendingDeleteId = null;

  const POLL_INTERVAL_MS = 3000;
  const MAX_ATTACHMENTS = 10;

  function deleteMessageUrl(messageId) {
    return `${messagesUrl.replace(/\/?$/, '')}/${messageId}/delete/`;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function scrollToBottom() {
    if (!messagesEl) return;
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function bindImageLoadScroll() {
    messagesEl?.querySelectorAll('.chat-message__attachment-image img').forEach((img) => {
      if (img.complete) return;
      img.addEventListener('load', scrollToBottom, { once: true });
    });
  }

  function initChatScroll() {
    scrollToBottom();
    bindImageLoadScroll();
    requestAnimationFrame(() => {
      scrollToBottom();
      requestAnimationFrame(scrollToBottom);
    });
  }

  function hideEmptyState() {
    const empty = messagesEl?.querySelector('[data-chat-empty]');
    if (empty) empty.remove();
  }

  function showEmptyStateIfNeeded() {
    if (!messagesEl) return;
    if (messagesEl.querySelector('[data-message-id]')) return;
    if (messagesEl.querySelector('[data-chat-empty]')) return;
    messagesEl.insertAdjacentHTML('beforeend', '<p class="chat-thread__empty" data-chat-empty>Сообщений пока нет.</p>');
  }

  function showError(text) {
    if (!errorEl) return;
    if (!text) {
      errorEl.hidden = true;
      errorEl.textContent = '';
      return;
    }
    errorEl.textContent = text;
    errorEl.hidden = false;
  }

  function getVisibleMessageIds() {
    if (!messagesEl) return [];
    return [...messagesEl.querySelectorAll('[data-message-id]')]
      .map((el) => Number(el.dataset.messageId))
      .filter((id) => !Number.isNaN(id));
  }

  function removeMessageFromDom(messageId) {
    const node = messagesEl?.querySelector(`[data-message-id="${messageId}"]`);
    node?.remove();
    showEmptyStateIfNeeded();
  }

  function closeContextMenu() {
    if (!contextMenu) return;
    contextMenu.hidden = true;
    contextMessage = null;
  }

  function openContextMenu(event, messageNode) {
    if (!contextMenu) return;
    event.preventDefault();
    contextMessage = {
      id: Number(messageNode.dataset.messageId),
      canDelete: messageNode.dataset.canDelete === '1',
      senderName: messageNode.dataset.senderName || '',
      preview: messageNode.dataset.messagePreview || '',
    };
    const deleteItem = contextMenu.querySelector('[data-chat-action="delete"]');
    if (deleteItem) deleteItem.hidden = !contextMessage.canDelete;
    contextMenu.hidden = false;
    const menuRect = contextMenu.getBoundingClientRect();
    let left = event.clientX;
    let top = event.clientY;
    if (left + menuRect.width > window.innerWidth - 8) {
      left = window.innerWidth - menuRect.width - 8;
    }
    if (top + menuRect.height > window.innerHeight - 8) {
      top = window.innerHeight - menuRect.height - 8;
    }
    contextMenu.style.left = `${left}px`;
    contextMenu.style.top = `${top}px`;
  }

  function openDeleteModal(messageId) {
    pendingDeleteId = messageId;
    if (deleteModal) deleteModal.hidden = false;
  }

  function closeDeleteModal() {
    pendingDeleteId = null;
    if (deleteModal) deleteModal.hidden = true;
  }

  function setReplyTarget(message) {
    replyTo = message;
    if (replyLabel) replyLabel.textContent = message.senderName;
    if (replyText) replyText.textContent = message.preview;
    if (replyPreview) replyPreview.hidden = false;
    input?.focus();
  }

  function clearReplyTarget() {
    replyTo = null;
    if (replyPreview) replyPreview.hidden = true;
    if (replyLabel) replyLabel.textContent = '';
    if (replyText) replyText.textContent = '';
  }

  function closeEmojiPicker() {
    if (!emojiPicker) return;
    emojiPicker.hidden = true;
    if (emojiToggleBtn) emojiToggleBtn.setAttribute('aria-expanded', 'false');
  }

  function positionEmojiPicker() {
    if (!emojiPicker || !emojiToggleBtn) return;
    emojiPicker.hidden = false;
    const rect = emojiToggleBtn.getBoundingClientRect();
    const pickerRect = emojiPicker.getBoundingClientRect();
    const margin = 8;
    let left = rect.left + rect.width / 2 - pickerRect.width / 2;
    let top = rect.top - pickerRect.height - margin;
    left = Math.max(margin, Math.min(left, window.innerWidth - pickerRect.width - margin));
    if (top < margin) {
      top = rect.bottom + margin;
    }
    emojiPicker.style.left = `${left}px`;
    emojiPicker.style.top = `${top}px`;
  }

  function openEmojiPicker() {
    if (!emojiPicker) return;
    emojiPicker.hidden = false;
    positionEmojiPicker();
    if (emojiToggleBtn) emojiToggleBtn.setAttribute('aria-expanded', 'true');
  }

  function toggleEmojiPicker() {
    if (!emojiPicker) return;
    if (emojiPicker.hidden) {
      openEmojiPicker();
    } else {
      closeEmojiPicker();
    }
  }

  function insertEmoji(emoji) {
    if (!input) return;
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;
    input.value = `${input.value.slice(0, start)}${emoji}${input.value.slice(end)}`;
    const caret = start + emoji.length;
    input.setSelectionRange(caret, caret);
    input.focus();
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function initEmojiPicker() {
    if (!emojiGrid) return;
    emojiGrid.innerHTML = CHAT_EMOJIS.map((emoji) => (
      `<button type="button" class="chat-emoji-picker__item" data-chat-emoji="${emoji}" aria-label="Вставить ${emoji}">${emoji}</button>`
    )).join('');
  }

  function messageClass(msg) {
    if (msg.is_system) return 'chat-message chat-message--system';
    if (msg.is_own) return 'chat-message chat-message--own';
    return 'chat-message chat-message--other';
  }

  function renderReplyQuote(reply) {
    if (!reply) return '';
    return `
      <div class="chat-message__reply">
        <span class="chat-message__reply-author">${escapeHtml(reply.sender_name)}</span>
        <span class="chat-message__reply-text">${escapeHtml(reply.text)}</span>
      </div>
    `;
  }

  function renderAttachment(attachment) {
    if (attachment.is_image) {
      const alt = escapeHtml(attachment.name || 'Изображение');
      return `<a href="${escapeHtml(attachment.url)}" class="chat-message__attachment-image" target="_blank" rel="noopener"><img src="${escapeHtml(attachment.url)}" alt="${alt}"></a>`;
    }
    const name = escapeHtml(attachment.name || 'Файл');
    return `<a href="${escapeHtml(attachment.url)}" class="chat-message__attachment-file" target="_blank" rel="noopener"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M12 18v-6M9 15l3 3 3-3"/></svg><span>${name}</span></a>`;
  }

  function renderAttachments(msg) {
    if (!msg.attachments?.length) return '';
    const items = msg.attachments.map(renderAttachment).join('');
    return `<div class="chat-message__attachments">${items}</div>`;
  }

  function systemBubbleClass(msg) {
    const base = 'chat-message__bubble chat-message__bubble--system';
    const variants = {
      started: 'chat-message__bubble--system-started',
      completed: 'chat-message__bubble--system-completed',
      cancelled: 'chat-message__bubble--system-cancelled',
    };
    const modifier = variants[msg.system_variant];
    return modifier ? `${base} ${modifier}` : base;
  }

  function systemIcon(msg) {
    const icons = {
      started: '▶',
      completed: '✓',
      cancelled: '✕',
    };
    return icons[msg.system_variant] || '📅';
  }

  const ratingUrlTemplate = thread.dataset.ratingUrlTemplate || '';

  function buildRatingUrl(bookingId) {
    return ratingUrlTemplate.replace('999999999', String(bookingId));
  }

  function renderStarsReadonly(rating) {
    return [1, 2, 3, 4, 5].map((value) => (
      `<span class="chat-session-rating__star${
        value <= rating ? ' chat-session-rating__star--filled' : ''
      }" aria-hidden="true">★</span>`
    )).join('');
  }

  function renderRatingDone(rating) {
    return `
      <div class="chat-session-rating chat-session-rating--done" data-session-rating>
        <p class="chat-session-rating__label">Ваша оценка:</p>
        <div class="chat-session-rating__stars chat-session-rating__stars--readonly" aria-label="${rating} из 5">
          ${renderStarsReadonly(rating)}
        </div>
      </div>
    `;
  }

  function renderSessionRating(msg) {
    const prompt = msg.rating_prompt;
    if (!prompt || !ratingUrlTemplate) return '';

    if (prompt.rating) {
      return renderRatingDone(prompt.rating);
    }
    if (!prompt.can_rate) return '';

    const stars = [1, 2, 3, 4, 5].map((value) => (
      `<button type="button"
              class="chat-session-rating__star"
              data-rating="${value}"
              aria-label="${value} из 5">★</button>`
    )).join('');

    return `
      <div class="chat-session-rating" data-session-rating data-booking-id="${prompt.booking_id}">
        <p class="chat-session-rating__label">Как прошло занятие?</p>
        <div class="chat-session-rating__stars" role="radiogroup" aria-label="Оценка занятия">
          ${stars}
        </div>
      </div>
    `;
  }

  function setStarHover(starsEl, value) {
    starsEl?.querySelectorAll('.chat-session-rating__star').forEach((star, index) => {
      star.classList.toggle('chat-session-rating__star--hover', index < value);
    });
  }

  async function submitSessionRating(container, rating) {
    const bookingId = container.dataset.bookingId;
    if (!bookingId || container.dataset.ratingSubmitting === '1') return;

    container.dataset.ratingSubmitting = '1';
    container.querySelectorAll('.chat-session-rating__star').forEach((star) => {
      star.disabled = true;
    });

    try {
      const formData = new FormData();
      formData.append('rating', String(rating));
      const response = await fetch(buildRatingUrl(bookingId), {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken || '' },
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || 'Не удалось отправить оценку.');
      }
      container.outerHTML = renderRatingDone(data.rating || rating);
    } catch (error) {
      container.dataset.ratingSubmitting = '0';
      container.querySelectorAll('.chat-session-rating__star').forEach((star) => {
        star.disabled = false;
      });
      showError(error.message || 'Не удалось отправить оценку.');
    }
  }

  function renderMessage(msg) {
    if (msg.is_system) {
      return `
        <div class="${messageClass(msg)}" data-message-id="${msg.id}">
          <div class="${systemBubbleClass(msg)}">
            <span class="chat-message__system-icon" aria-hidden="true">${systemIcon(msg)}</span>
            ${escapeHtml(msg.text)}
          </div>
          ${renderSessionRating(msg)}
        </div>
      `;
    }

    const textBlock = msg.text
      ? `<p class="chat-message__text">${escapeHtml(msg.text).replace(/\n/g, '<br>')}</p>`
      : '';

    return `
      <div class="${messageClass(msg)}"
           data-message-id="${msg.id}"
           data-context-menu="1"
           data-can-delete="${msg.can_delete ? '1' : '0'}"
           data-sender-name="${escapeHtml(msg.sender_name || '')}"
           data-message-preview="${escapeHtml(msg.preview || '')}">
        <div class="chat-message__bubble">
          ${renderReplyQuote(msg.reply_to)}
          ${renderAttachments(msg)}
          ${textBlock}
          <time class="chat-message__time" datetime="${escapeHtml(msg.created_at)}">${escapeHtml(window.ChatDateTime?.formatMessageTime(msg.created_at) || '')}</time>
        </div>
      </div>
    `;
  }

  function appendMessages(items) {
    if (!items.length || !messagesEl) return;
    hideEmptyState();
    const html = items.map(renderMessage).join('');
    messagesEl.insertAdjacentHTML('beforeend', html);
    lastMessageId = items[items.length - 1].id;
    thread.dataset.lastMessageId = String(lastMessageId);
    scrollToBottom();
    bindImageLoadScroll();
  }

  function renderPreview() {
    if (!previewList) return;
    if (!pendingFiles.length) {
      previewList.hidden = true;
      previewList.innerHTML = '';
      return;
    }
    previewList.hidden = false;
    previewList.innerHTML = pendingFiles.map((file, index) => `
      <div class="chat-composer__preview-item">
        <span class="chat-composer__preview-name">${escapeHtml(file.name)}</span>
        <button type="button" class="chat-composer__preview-remove" data-chat-preview-remove="${index}" aria-label="Убрать файл">×</button>
      </div>
    `).join('');
  }

  function clearAttachments() {
    pendingFiles = [];
    if (fileInput) fileInput.value = '';
    renderPreview();
  }

  function addAttachments(files) {
    const available = MAX_ATTACHMENTS - pendingFiles.length;
    if (available <= 0) {
      showError(`Можно прикрепить не больше ${MAX_ATTACHMENTS} файлов за раз.`);
      return;
    }
    const nextFiles = [...files].slice(0, available);
    if (files.length > available) {
      showError(`Добавлено ${nextFiles.length} из ${files.length}: лимит — ${MAX_ATTACHMENTS} файлов.`);
    } else {
      showError('');
    }
    pendingFiles.push(...nextFiles);
    renderPreview();
  }

  async function pollMessages() {
    try {
      const visible = getVisibleMessageIds().join(',');
      const params = new URLSearchParams({ after: String(lastMessageId) });
      if (visible) params.set('visible', visible);
      const res = await fetch(`${messagesUrl}?${params.toString()}`, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.deleted_ids?.length) {
        data.deleted_ids.forEach(removeMessageFromDom);
      }
      if (data.messages?.length) {
        appendMessages(data.messages);
      }
    } catch {
      /* ignore transient network errors */
    }
  }

  async function deleteMessage(messageId) {
    showError('');
    try {
      const body = new FormData();
      if (csrfToken) body.append('csrfmiddlewaretoken', csrfToken);
      const res = await fetch(deleteMessageUrl(messageId), {
        method: 'POST',
        body,
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      const data = await res.json();
      if (!res.ok) {
        showError(data.error || 'Не удалось удалить сообщение.');
        return;
      }
      removeMessageFromDom(messageId);
    } catch {
      showError('Не удалось удалить сообщение. Проверьте соединение.');
    }
  }

  async function sendMessage() {
    if (sending || !form) return;
    const text = input?.value.trim() || '';
    if (!text && !pendingFiles.length) {
      showError('Напишите сообщение или прикрепите файл.');
      return;
    }

    sending = true;
    showError('');
    if (sendBtn) sendBtn.disabled = true;

    const body = new FormData();
    body.append('text', text);
    if (replyTo?.id) body.append('reply_to', String(replyTo.id));
    pendingFiles.forEach((file) => body.append('attachments', file));
    if (csrfToken) body.append('csrfmiddlewaretoken', csrfToken);

    try {
      const res = await fetch(messagesUrl, {
        method: 'POST',
        body,
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      const data = await res.json();
      if (!res.ok) {
        showError(data.error || 'Не удалось отправить сообщение.');
        return;
      }
      if (data.message) {
        appendMessages([data.message]);
      }
      if (input) input.value = '';
      clearAttachments();
      clearReplyTarget();
    } catch {
      showError('Не удалось отправить сообщение. Проверьте соединение.');
    } finally {
      sending = false;
      if (sendBtn) sendBtn.disabled = false;
      input?.focus();
    }
  }

  form?.addEventListener('submit', (event) => {
    event.preventDefault();
    sendMessage();
  });

  input?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  attachBtn?.addEventListener('click', () => {
    closeEmojiPicker();
    fileInput?.click();
  });

  emojiToggleBtn?.addEventListener('click', (event) => {
    event.stopPropagation();
    toggleEmojiPicker();
  });

  emojiGrid?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-chat-emoji]');
    if (!button) return;
    insertEmoji(button.dataset.chatEmoji || '');
    closeEmojiPicker();
  });

  fileInput?.addEventListener('change', () => {
    const files = [...(fileInput.files || [])];
    if (files.length) {
      addAttachments(files);
      fileInput.value = '';
    }
  });

  previewList?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-chat-preview-remove]');
    if (!button) return;
    const index = Number(button.dataset.chatPreviewRemove);
    if (Number.isNaN(index)) return;
    pendingFiles.splice(index, 1);
    renderPreview();
    showError('');
  });

  replyCancelBtn?.addEventListener('click', clearReplyTarget);

  messagesEl?.addEventListener('mouseover', (event) => {
    const star = event.target.closest('.chat-session-rating__star[data-rating]');
    if (!star || star.disabled) return;
    const starsEl = star.closest('.chat-session-rating__stars');
    setStarHover(starsEl, Number(star.dataset.rating));
  });

  messagesEl?.addEventListener('mouseout', (event) => {
    const starsEl = event.target.closest('.chat-session-rating__stars');
    if (!starsEl || starsEl.classList.contains('chat-session-rating__stars--readonly')) return;
    if (event.relatedTarget && starsEl.contains(event.relatedTarget)) return;
    setStarHover(starsEl, 0);
  });

  messagesEl?.addEventListener('click', (event) => {
    const star = event.target.closest('.chat-session-rating__star[data-rating]');
    if (!star || star.disabled) return;
    const container = star.closest('[data-session-rating]');
    if (!container || container.classList.contains('chat-session-rating--done')) return;
    submitSessionRating(container, Number(star.dataset.rating));
  });

  messagesEl?.addEventListener('contextmenu', (event) => {
    if (event.target.closest('a')) return;
    const messageNode = event.target.closest('[data-context-menu]');
    if (!messageNode) return;
    openContextMenu(event, messageNode);
  });

  contextMenu?.addEventListener('click', (event) => {
    const actionBtn = event.target.closest('[data-chat-action]');
    if (!actionBtn || !contextMessage) return;
    const action = actionBtn.dataset.chatAction;
    if (action === 'reply') {
      setReplyTarget(contextMessage);
    } else if (action === 'delete') {
      openDeleteModal(contextMessage.id);
    }
    closeContextMenu();
  });

  deleteConfirmBtn?.addEventListener('click', async () => {
    if (!pendingDeleteId) return;
    const messageId = pendingDeleteId;
    closeDeleteModal();
    await deleteMessage(messageId);
  });

  deleteModal?.querySelectorAll('[data-chat-modal-close]').forEach((btn) => {
    btn.addEventListener('click', closeDeleteModal);
  });

  document.addEventListener('click', (event) => {
    if (!contextMenu?.hidden && !event.target.closest('[data-chat-context-menu]')) {
      closeContextMenu();
    }
    if (!emojiPicker?.hidden
      && !event.target.closest('[data-chat-emoji-picker]')
      && !event.target.closest('[data-chat-emoji-toggle]')) {
      closeEmojiPicker();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeContextMenu();
      closeDeleteModal();
      closeEmojiPicker();
    }
  });

  messagesEl?.addEventListener('scroll', () => {
    closeContextMenu();
    if (!emojiPicker?.hidden) positionEmojiPicker();
  }, { passive: true });

  window.addEventListener('resize', () => {
    if (!emojiPicker?.hidden) positionEmojiPicker();
  });

  if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
  }

  window.ChatDateTime?.applyLocalTimes(thread);
  initEmojiPicker();
  initChatScroll();
  window.addEventListener('load', initChatScroll);
  window.addEventListener('pageshow', initChatScroll);

  pollTimer = window.setInterval(pollMessages, POLL_INTERVAL_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') pollMessages();
  });
})();
