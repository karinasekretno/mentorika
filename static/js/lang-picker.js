(function () {
  function initLangPicker(root) {
    var trigger = root.querySelector('.lang-picker__trigger');
    var dropdown = root.querySelector('.lang-picker__dropdown');
    var search = root.querySelector('.lang-picker__search');
    var items = root.querySelectorAll('.lang-picker__item');
    var emptyState = root.querySelector('.lang-picker__empty');
    var tagsContainer = root.querySelector('.lang-picker__tags');
    var checkboxes = root.querySelectorAll('input[type="checkbox"][name="languages"]');

    function renderTags() {
      if (!tagsContainer) return;
      tagsContainer.innerHTML = '';
      checkboxes.forEach(function (cb) {
        if (!cb.checked) return;
        var tag = document.createElement('span');
        tag.className = 'mentor-lang-tag';
        tag.textContent = cb.value.toUpperCase();
        tagsContainer.appendChild(tag);
      });
    }

    function filterItems(query) {
      var q = query.trim().toLowerCase();
      var visible = 0;
      items.forEach(function (item) {
        var label = item.getAttribute('data-label') || '';
        var match = !q || label.indexOf(q) !== -1;
        item.hidden = !match;
        if (match) visible += 1;
      });
      if (emptyState) emptyState.hidden = visible > 0;
    }

    function openDropdown() {
      dropdown.hidden = false;
      trigger.setAttribute('aria-expanded', 'true');
      search.value = '';
      filterItems('');
      search.focus();
    }

    function closeDropdown() {
      dropdown.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
    }

    trigger.addEventListener('click', function () {
      if (dropdown.hidden) openDropdown();
      else closeDropdown();
    });

    search.addEventListener('input', function () {
      filterItems(search.value);
    });

    search.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeDropdown();
        trigger.focus();
      }
    });

    checkboxes.forEach(function (cb) {
      cb.addEventListener('change', renderTags);
    });

    document.addEventListener('click', function (e) {
      if (!root.contains(e.target)) closeDropdown();
    });

    renderTags();
  }

  document.querySelectorAll('[data-lang-picker]').forEach(initLangPicker);
})();
