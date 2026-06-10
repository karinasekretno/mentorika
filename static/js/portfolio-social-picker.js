(function () {
  function initRepeater(config) {
    var rowsWrap = config.rowsWrap;
    var addBtn = config.addBtn;
    var rowTemplate = config.rowTemplate;
    var maxLinks = config.maxLinks;
    var rowSelector = config.rowSelector;
    var urlSelector = config.urlSelector;
    var removeSelector = config.removeSelector;
    var namePrefix = config.namePrefix;
    var nameFields = config.nameFields;

    function getRows() {
      return rowsWrap.querySelectorAll(rowSelector);
    }

    function assignFieldNames() {
      getRows().forEach(function (row, index) {
        nameFields.forEach(function (field) {
          var el = row.querySelector(field.selector);
          if (el) el.name = field.prefix + index + field.suffix;
        });
      });
    }

    function rowHasUrl(row) {
      var input = row.querySelector(urlSelector);
      return input && input.value.trim();
    }

    function updateAddButtonVisibility() {
      var rows = getRows();
      if (rows.length >= maxLinks) {
        addBtn.hidden = true;
        return;
      }
      var lastRow = rows[rows.length - 1];
      addBtn.hidden = !(lastRow && rowHasUrl(lastRow));
    }

    function clearRow(row) {
      row.querySelectorAll('input, select').forEach(function (el) {
        if (el.tagName === 'SELECT') {
          el.selectedIndex = 0;
        } else {
          el.value = '';
        }
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
      var urlInput = row.querySelector(urlSelector);
      var removeBtn = row.querySelector(removeSelector);
      urlInput.addEventListener('input', updateAddButtonVisibility);
      if (removeBtn) {
        removeBtn.addEventListener('click', function () {
          removeRow(row);
        });
      }
    }

    function addRow(data) {
      if (getRows().length >= maxLinks) return;
      var clone = rowTemplate.content.cloneNode(true);
      rowsWrap.appendChild(clone);
      var newRow = rowsWrap.lastElementChild;
      if (data) {
        nameFields.forEach(function (field) {
          if (!data[field.key]) return;
          var el = newRow.querySelector(field.selector);
          if (el) el.value = data[field.key];
        });
      }
      assignFieldNames();
      bindRow(newRow);
      updateAddButtonVisibility();
      if (!data || !data.url) {
        newRow.querySelector(urlSelector).focus();
      }
    }

    addBtn.addEventListener('click', function () {
      addRow(null);
    });

    getRows().forEach(bindRow);
    assignFieldNames();
    updateAddButtonVisibility();

    return { addRow: addRow };
  }

  function initPortfolioPicker(root) {
    initRepeater({
      rowsWrap: root.querySelector('[data-portfolio-rows]'),
      addBtn: root.querySelector('.portfolio-picker__add'),
      rowTemplate: root.querySelector('.portfolio-picker__template'),
      maxLinks: parseInt(root.querySelector('[data-portfolio-rows]').getAttribute('data-max-links') || '10', 10),
      rowSelector: '[data-portfolio-row]',
      urlSelector: '.portfolio-picker__url',
      removeSelector: '.portfolio-picker__remove',
      nameFields: [
        { selector: '.portfolio-picker__url', prefix: 'portfolio_link_', suffix: '', key: 'url' },
      ],
    });
  }

  document.querySelectorAll('[data-portfolio-picker]').forEach(initPortfolioPicker);
})();
