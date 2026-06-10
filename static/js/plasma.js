document.addEventListener('DOMContentLoaded', () => {
  const html = document.documentElement;

  html.setAttribute('data-theme', 'eva');

  /* ---- Dark mode toggle ---- */
  const darkSwitch = document.getElementById('dark-mode-switch');
  const savedScheme = localStorage.getItem('plasma-color-scheme') || 'light';
  html.setAttribute('data-color-scheme', savedScheme);
  if (darkSwitch) {
    darkSwitch.classList.toggle('plasma-switch--on', savedScheme === 'dark');
    darkSwitch.addEventListener('click', () => {
      const isDark = darkSwitch.classList.toggle('plasma-switch--on');
      const scheme = isDark ? 'dark' : 'light';
      html.setAttribute('data-color-scheme', scheme);
      localStorage.setItem('plasma-color-scheme', scheme);
    });
  }

  /* ---- Tabs (mentors filter) ---- */
  const mentorTabs = document.querySelectorAll('[data-mentor-tab]');
  mentorTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      mentorTabs.forEach(t => t.classList.remove('plasma-tabs__item--active'));
      tab.classList.add('plasma-tabs__item--active');
    });
  });

  /* ---- Progress animation on scroll ---- */
  const progressBars = document.querySelectorAll('.plasma-progress__bar');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.width = entry.target.dataset.width || '0%';
      }
    });
  }, { threshold: 0.5 });

  progressBars.forEach(bar => {
    bar.style.width = '0%';
    observer.observe(bar);
  });

  /* ---- Notifications ---- */
  const NOTIFICATION_LIFETIME_MS = 10000;
  const NOTIFICATION_EXIT_MS = 300;

  const notifyBtn = document.getElementById('notify-demo');
  const notifyContainer = document.getElementById('notification-container');

  function dismissNotification(el) {
    if (!el || el.classList.contains('plasma-notification--leaving')) return;
    el.classList.add('plasma-notification--leaving');
    window.setTimeout(() => {
      const container = el.parentElement;
      el.remove();
      if (container?.id === 'flash-messages' && !container.children.length) {
        container.remove();
      }
    }, NOTIFICATION_EXIT_MS);
  }

  function scheduleNotificationDismiss(el) {
    window.setTimeout(() => dismissNotification(el), NOTIFICATION_LIFETIME_MS);
  }

  function showNotification(type, message) {
    const el = document.createElement('div');
    el.className = `plasma-notification plasma-notification--${type}`;
    el.innerHTML = `<span class="text-body-s">${message}</span>`;
    notifyContainer?.appendChild(el);
    scheduleNotificationDismiss(el);
  }

  document.querySelectorAll('.plasma-notification').forEach(scheduleNotificationDismiss);

  notifyBtn?.addEventListener('click', () => {
    const types = ['success', 'info', 'warning', 'critical'];
    const messages = [
      'Заявка успешно отправлена!',
      'Новый ментор доступен для записи',
      'Осталось 2 свободных слота',
      'Сессия отменена ментором',
    ];
    const idx = Math.floor(Math.random() * types.length);
    showNotification(types[idx], messages[idx]);
  });

  /* ---- Smooth scroll for nav links ---- */
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', e => {
      const target = document.querySelector(link.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  /* ---- Header scroll shadow ---- */
  const header = document.querySelector('.plasma-header');
  window.addEventListener('scroll', () => {
    header?.classList.toggle('plasma-header--scrolled', window.scrollY > 10);
  });
});
