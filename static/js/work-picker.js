(function () {
  function initWorkPeriod(periodWrap) {
    if (periodWrap.dataset.periodInit) return;
    periodWrap.dataset.periodInit = '1';

    var endInput = periodWrap.querySelector('.work-picker__end');
    var currentCb = periodWrap.querySelector('.work-picker__current-cb');

    function syncEndState() {
      var isCurrent = currentCb.checked;
      endInput.disabled = isCurrent;
      if (isCurrent) endInput.value = '';
    }

    currentCb.addEventListener('change', syncEndState);
    syncEndState();
  }

  function initWorkPicker(root) {
    var maxWorks = parseInt(root.getAttribute('data-max-works') || '20', 10);
    var rowsWrap = root.querySelector('.work-picker__rows');
    var addBtn = root.querySelector('.work-picker__add');
    var rowTemplate = root.querySelector('.work-picker__template');

    function getRows() {
      return rowsWrap.querySelectorAll('[data-work-row]');
    }

    function assignFieldNames() {
      getRows().forEach(function (row, index) {
        var company = row.querySelector('.work-picker__company');
        var start = row.querySelector('.work-picker__start');
        var end = row.querySelector('.work-picker__end');
        var currentCb = row.querySelector('.work-picker__current-cb');
        var jobTitle = row.querySelector('.work-picker__job-title');
        var description = row.querySelector('.work-picker__description');
        if (company) company.name = 'work_experience_' + index + '_company';
        if (start) start.name = 'work_experience_' + index + '_start';
        if (end) end.name = 'work_experience_' + index + '_end';
        if (currentCb) currentCb.name = 'work_experience_' + index + '_is_current';
        if (jobTitle) jobTitle.name = 'work_experience_' + index + '_job_title';
        if (description) description.name = 'work_experience_' + index + '_description';
      });
    }

    function rowHasCompany(row) {
      var company = row.querySelector('.work-picker__company');
      return company && company.value.trim();
    }

    function updateAddButtonVisibility() {
      var rows = getRows();
      var canAddMore = rows.length < maxWorks;

      if (!canAddMore) {
        addBtn.hidden = true;
        return;
      }

      var lastRow = rows[rows.length - 1];
      addBtn.hidden = !(lastRow && rowHasCompany(lastRow));
    }

    function clearRow(row) {
      row.querySelectorAll('input:not([type="checkbox"]), textarea').forEach(function (el) {
        el.value = '';
        el.disabled = false;
      });
      row.querySelectorAll('input[type="checkbox"]').forEach(function (el) {
        el.checked = false;
      });
      var periodWrap = row.querySelector('[data-work-period]');
      if (periodWrap) {
        var endInput = periodWrap.querySelector('.work-picker__end');
        endInput.disabled = false;
      }
      updateAddButtonVisibility();
    }

    function removeRow(row) {
      if (getRows().length === 1) {
        clearRow(row);
        return;
      }
      row.remove();
      assignFieldNames();
      updateAddButtonVisibility();
    }

    function bindRow(row) {
      var company = row.querySelector('.work-picker__company');
      var removeBtn = row.querySelector('.work-picker__remove');
      var periodWrap = row.querySelector('[data-work-period]');

      company.addEventListener('input', updateAddButtonVisibility);
      if (periodWrap) initWorkPeriod(periodWrap);
      if (removeBtn) {
        removeBtn.addEventListener('click', function () {
          removeRow(row);
        });
      }
    }

    function addRow(data) {
      if (getRows().length >= maxWorks) return;

      var clone = rowTemplate.content.cloneNode(true);
      rowsWrap.appendChild(clone);

      var newRow = rowsWrap.lastElementChild;
      if (data) {
        if (data.company) newRow.querySelector('.work-picker__company').value = data.company;
        if (data.start) newRow.querySelector('.work-picker__start').value = data.start;
        if (data.end) newRow.querySelector('.work-picker__end').value = data.end;
        if (data.is_current) newRow.querySelector('.work-picker__current-cb').checked = true;
        if (data.job_title) newRow.querySelector('.work-picker__job-title').value = data.job_title;
        if (data.description) newRow.querySelector('.work-picker__description').value = data.description;
      }

      assignFieldNames();
      bindRow(newRow);
      updateAddButtonVisibility();

      if (!data || !data.company) {
        newRow.querySelector('.work-picker__company').focus();
      }
    }

    addBtn.addEventListener('click', function () {
      addRow(null);
    });

    getRows().forEach(bindRow);
    assignFieldNames();
    updateAddButtonVisibility();
  }

  document.querySelectorAll('[data-work-picker]').forEach(initWorkPicker);
})();
