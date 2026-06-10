(function () {
  var LEVEL_LABELS = {
    junior: 'JUNIOR',
    middle: 'MIDDLE',
    senior: 'SENIOR',
    lead: 'LEAD',
  };

  function initSkillPicker(root) {
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
      return root.querySelectorAll('input[type="checkbox"][name="skills"]');
    }

    function getLevelSelect(checkbox) {
      var name = checkbox.getAttribute('data-skill-name');
      return root.querySelector('select[data-skill-level-for="' + name + '"]');
    }

    function getCustomRows() {
      return customRowsWrap.querySelectorAll('[data-custom-row]');
    }

    function usedCustomCount() {
      var count = 0;
      getCustomRows().forEach(function (row) {
        var input = row.querySelector('.skill-picker__custom-name');
        if (input && input.value.trim()) count += 1;
      });
      return count;
    }

    function assignCustomFieldNames() {
      getCustomRows().forEach(function (row, index) {
        var input = row.querySelector('.skill-picker__custom-name');
        var select = row.querySelector('.skill-picker__custom-level');
        if (input) input.name = 'custom_skill_' + index + '_name';
        if (select) select.name = 'custom_skill_' + index + '_level';
      });
    }

    function updateAddButtonVisibility() {
      var rows = getCustomRows();
      var canAddMore = rows.length < maxCustom;

      if (!canAddMore) {
        addCustomBtn.hidden = true;
        return;
      }

      if (rows.length === 0) {
        addCustomBtn.hidden = false;
        return;
      }

      var lastRow = rows[rows.length - 1];
      var lastInput = lastRow.querySelector('.skill-picker__custom-name');
      addCustomBtn.hidden = !(lastInput && lastInput.value.trim());
    }

    function renderTags() {
      if (!tagsContainer) return;
      tagsContainer.innerHTML = '';

      getCatalogCheckboxes().forEach(function (cb) {
        if (!cb.checked) return;
        var levelSelect = getLevelSelect(cb);
        var level = levelSelect ? levelSelect.value : 'middle';
        var tag = document.createElement('span');
        tag.className = 'mentor-skill-tag';
        tag.textContent = cb.value.toUpperCase() + ' - ' + (LEVEL_LABELS[level] || level.toUpperCase());
        tagsContainer.appendChild(tag);
      });

      getCustomRows().forEach(function (row) {
        var input = row.querySelector('.skill-picker__custom-name');
        var select = row.querySelector('.skill-picker__custom-level');
        if (!input || !input.value.trim()) return;
        var level = select ? select.value : 'middle';
        var tag = document.createElement('span');
        tag.className = 'mentor-skill-tag';
        tag.textContent = input.value.trim().toUpperCase() + ' - ' + (LEVEL_LABELS[level] || level.toUpperCase());
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
      var select = row.querySelector('.skill-picker__custom-level');
      var removeBtn = row.querySelector('.skill-picker__custom-remove');

      input.addEventListener('input', function () {
        updateAddButtonVisibility();
        renderTags();
      });
      select.addEventListener('change', renderTags);
      if (removeBtn) {
        removeBtn.addEventListener('click', function () {
          removeCustomRow(row);
        });
      }
    }

    function addCustomRow(name, level) {
      if (getCustomRows().length >= maxCustom) return;

      var clone = rowTemplate.content.cloneNode(true);
      customRowsWrap.appendChild(clone);

      var newRow = customRowsWrap.lastElementChild;
      var input = newRow.querySelector('.skill-picker__custom-name');
      var select = newRow.querySelector('.skill-picker__custom-level');

      if (name) input.value = name;
      if (level) select.value = level;

      assignCustomFieldNames();
      bindCustomRow(newRow);
      updateAddButtonVisibility();
      renderTags();

      if (!name) input.focus();
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
      cb.addEventListener('change', function () {
        var levelSelect = getLevelSelect(cb);
        if (levelSelect) levelSelect.disabled = !cb.checked;
        renderTags();
      });
    });

    root.querySelectorAll('.skill-picker__level').forEach(function (select) {
      select.addEventListener('change', renderTags);
    });

    addCustomBtn.addEventListener('click', function () {
      addCustomRow('', 'middle');
    });

    getCustomRows().forEach(bindCustomRow);
    assignCustomFieldNames();
    updateAddButtonVisibility();

    document.addEventListener('click', function (e) {
      if (!root.contains(e.target)) closeDropdown();
    });

    renderTags();
  }

  document.querySelectorAll('[data-skill-picker]').forEach(initSkillPicker);
})();
