(function () {
  function initEducationPicker(root) {
    var maxEntries = parseInt(root.getAttribute('data-max-entries') || '20', 10);
    var rowsWrap = root.querySelector('.education-picker__rows');
    var addBtn = root.querySelector('.education-picker__add');
    var rowTemplate = root.querySelector('.education-picker__template');

    function getRows() {
      return rowsWrap.querySelectorAll('[data-education-row]');
    }

    function assignFieldNames() {
      getRows().forEach(function (row, index) {
        var institution = row.querySelector('.education-picker__institution');
        var year = row.querySelector('.education-picker__year');
        var specialization = row.querySelector('.education-picker__specialization');
        if (institution) institution.name = 'education_' + index + '_institution';
        if (year) year.name = 'education_' + index + '_graduation_year';
        if (specialization) specialization.name = 'education_' + index + '_specialization';
      });
    }

    function rowHasInstitution(row) {
      var institution = row.querySelector('.education-picker__institution');
      return institution && institution.value.trim();
    }

    function updateAddButtonVisibility() {
      var rows = getRows();
      var canAddMore = rows.length < maxEntries;

      if (!canAddMore) {
        addBtn.hidden = true;
        return;
      }

      var lastRow = rows[rows.length - 1];
      addBtn.hidden = !(lastRow && rowHasInstitution(lastRow));
    }

    function clearRow(row) {
      row.querySelectorAll('input').forEach(function (el) {
        el.value = '';
      });
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
      var institution = row.querySelector('.education-picker__institution');
      var removeBtn = row.querySelector('.education-picker__remove');

      institution.addEventListener('input', updateAddButtonVisibility);
      if (removeBtn) {
        removeBtn.addEventListener('click', function () {
          removeRow(row);
        });
      }
    }

    function addRow(data) {
      if (getRows().length >= maxEntries) return;

      var clone = rowTemplate.content.cloneNode(true);
      rowsWrap.appendChild(clone);

      var newRow = rowsWrap.lastElementChild;
      if (data) {
        if (data.institution) newRow.querySelector('.education-picker__institution').value = data.institution;
        if (data.graduation_year) newRow.querySelector('.education-picker__year').value = data.graduation_year;
        if (data.specialization) newRow.querySelector('.education-picker__specialization').value = data.specialization;
      }

      assignFieldNames();
      bindRow(newRow);
      updateAddButtonVisibility();

      if (!data || !data.institution) {
        newRow.querySelector('.education-picker__institution').focus();
      }
    }

    addBtn.addEventListener('click', function () {
      addRow(null);
    });

    getRows().forEach(bindRow);
    assignFieldNames();
    updateAddButtonVisibility();
  }

  document.querySelectorAll('[data-education-picker]').forEach(initEducationPicker);
})();
