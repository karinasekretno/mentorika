(function () {
  function initInterestPicker(root) {
    var maxCustom = parseInt(root.getAttribute('data-max-custom') || '10', 10);
    var trigger = root.querySelector('.skill-picker__trigger');
    var dropdown = root.querySelector('.skill-picker__dropdown');
    var search = root.querySelector('.skill-picker__search');
    var items = root.querySelectorAll('.skill-picker__item');
    var emptyState = root.querySelector('.skill-picker__empty');
    var tagsContainer = root.querySelector('.skill-picker__tags');
    var customRowsWrap = root.querySelector('.skill-picker__custom-rows');
    var addCustomBtn = root.querySelector('.skill-picker__add-custom');
    var rowTemplate = root.querySelector('.skill-picker__custom-template');

    function getCatalogCheckboxes() {
      return root.querySelectorAll('input[type="checkbox"][name="interests"]');
    }

    function getCustomRows() {
      return customRowsWrap.querySelectorAll('[data-custom-row]');
    }

    function assignCustomFieldNames() {
      getCustomRows().forEach(function (row, index) {
        var input = row.querySelector('.skill-picker__custom-name');
        if (input) input.name = 'custom_interest_' + index + '_name';
      });
    }

    function updateAddButtonVisibility() {
      var rows = getCustomRows();
      if (rows.length >= maxCustom) {
        addCustomBtn.hidden = true;
        return;
      }
      if (!rows.length) {
        addCustomBtn.hidden = false;
        return;
      }
      var lastInput = rows[rows.length - 1].querySelector('.skill-picker__custom-name');
      addCustomBtn.hidden = !(lastInput && lastInput.value.trim());
    }

    function renderTags() {
      if (!tagsContainer) return;
      tagsContainer.innerHTML = '';

      getCatalogCheckboxes().forEach(function (cb) {
        if (!cb.checked) return;
        var tag = document.createElement('span');
        tag.className = 'mentor-skill-tag';
        tag.textContent = cb.value.toUpperCase();
        tagsContainer.appendChild(tag);
      });

      getCustomRows().forEach(function (row) {
        var input = row.querySelector('.skill-picker__custom-name');
        if (!input || !input.value.trim()) return;
        var tag = document.createElement('span');
        tag.className = 'mentor-skill-tag';
        tag.textContent = input.value.trim().toUpperCase();
        tagsContainer.appendChild(tag);
      });
    }

    function removeCustomRow(row) {
      row.remove();
      assignCustomFieldNames();
      updateAddButtonVisibility();
      renderTags();
    }

    function bindCustomRow(row) {
      var input = row.querySelector('.skill-picker__custom-name');
      var removeBtn = row.querySelector('.skill-picker__custom-remove');
      input.addEventListener('input', function () {
        updateAddButtonVisibility();
        renderTags();
      });
      if (removeBtn) {
        removeBtn.addEventListener('click', function () {
          removeCustomRow(row);
        });
      }
    }

    function addCustomRow(name) {
      if (getCustomRows().length >= maxCustom) return;
      var clone = rowTemplate.content.cloneNode(true);
      customRowsWrap.appendChild(clone);
      var newRow = customRowsWrap.lastElementChild;
      if (name) newRow.querySelector('.skill-picker__custom-name').value = name;
      assignCustomFieldNames();
      bindCustomRow(newRow);
      updateAddButtonVisibility();
      renderTags();
      if (!name) newRow.querySelector('.skill-picker__custom-name').focus();
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

    getCatalogCheckboxes().forEach(function (cb) {
      cb.addEventListener('change', renderTags);
    });

    addCustomBtn.addEventListener('click', function () {
      addCustomRow('');
    });

    getCustomRows().forEach(bindCustomRow);
    assignCustomFieldNames();
    updateAddButtonVisibility();

    document.addEventListener('click', function (e) {
      if (!root.contains(e.target)) closeDropdown();
    });

    renderTags();
  }

  document.querySelectorAll('[data-interest-picker]').forEach(initInterestPicker);
})();
