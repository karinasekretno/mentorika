(function () {
  function initTopicPicker(root) {
    var maxTopics = parseInt(root.getAttribute('data-max-topics') || '20', 10);
    var rowsWrap = root.querySelector('.topic-picker__rows');
    var addBtn = root.querySelector('.topic-picker__add');
    var rowTemplate = root.querySelector('.topic-picker__template');

    function getRows() {
      return rowsWrap.querySelectorAll('[data-topic-row]');
    }

    function assignFieldNames() {
      getRows().forEach(function (row, index) {
        var textInput = row.querySelector('.topic-picker__text');
        if (textInput) textInput.name = 'consultation_topic_' + index;
      });
    }

    function rowHasText(row) {
      var textInput = row.querySelector('.topic-picker__text');
      return textInput && textInput.value.trim();
    }

    function updateAddButtonVisibility() {
      var rows = getRows();
      var canAddMore = rows.length < maxTopics;

      if (!canAddMore) {
        addBtn.hidden = true;
        return;
      }

      var lastRow = rows[rows.length - 1];
      addBtn.hidden = !(lastRow && rowHasText(lastRow));
    }

    function removeRow(row) {
      var rows = getRows();
      if (rows.length === 1) {
        var textInput = row.querySelector('.topic-picker__text');
        if (textInput) textInput.value = '';
        updateAddButtonVisibility();
        return;
      }
      row.remove();
      assignFieldNames();
      updateAddButtonVisibility();
    }

    function bindRow(row) {
      var textInput = row.querySelector('.topic-picker__text');
      var removeBtn = row.querySelector('.topic-picker__remove');

      textInput.addEventListener('input', updateAddButtonVisibility);
      if (removeBtn) {
        removeBtn.addEventListener('click', function () {
          removeRow(row);
        });
      }
    }

    function addRow(text) {
      if (getRows().length >= maxTopics) return;

      var clone = rowTemplate.content.cloneNode(true);
      rowsWrap.appendChild(clone);

      var newRow = rowsWrap.lastElementChild;
      var textInput = newRow.querySelector('.topic-picker__text');

      if (text) textInput.value = text;

      assignFieldNames();
      bindRow(newRow);
      updateAddButtonVisibility();

      if (!text) textInput.focus();
    }

    addBtn.addEventListener('click', function () {
      addRow('');
    });

    getRows().forEach(bindRow);
    assignFieldNames();
    updateAddButtonVisibility();
  }

  document.querySelectorAll('[data-topic-picker]').forEach(initTopicPicker);
})();
