(function () {
  function initSocialPicker(root) {
    var mainUrlsWrap = root.querySelector('[data-social-main-urls]');
    var otherWrap = root.querySelector('[data-social-other]');
    var otherRowsWrap = root.querySelector('[data-social-other-rows]');
    var addOtherBtn = root.querySelector('[data-social-add-other]');
    var otherTemplate = root.querySelector('.social-picker__other-template');
    var otherStartIndex = parseInt(root.getAttribute('data-other-start') || '7', 10);
    var maxLinks = parseInt(root.getAttribute('data-max-links') || '10', 10);
    var iconButtons = root.querySelectorAll('[data-social-icon]');

    function getMainUrlRows() {
      return mainUrlsWrap.querySelectorAll('[data-social-url-row]');
    }

    function getOtherRows() {
      return otherRowsWrap ? otherRowsWrap.querySelectorAll('[data-social-other-row]') : [];
    }

    function getTotalLinkCount() {
      var mainFilled = 0;
      getMainUrlRows().forEach(function (row) {
        var input = row.querySelector('.social-picker__url');
        if (input && input.value.trim()) mainFilled += 1;
      });
      return mainFilled + getOtherRows().length;
    }

    function getNextOtherIndex() {
      var rows = getOtherRows();
      if (!rows.length) return otherStartIndex;
      var maxIndex = otherStartIndex - 1;
      rows.forEach(function (row) {
        var platformInput = row.querySelector('.social-picker__platform-input');
        if (!platformInput || !platformInput.name) return;
        var match = platformInput.name.match(/social_link_(\d+)_platform/);
        if (match) maxIndex = Math.max(maxIndex, parseInt(match[1], 10));
      });
      return maxIndex + 1;
    }

    function assignOtherFieldNames() {
      if (!otherRowsWrap) return;
      var index = otherStartIndex;
      getOtherRows().forEach(function (row) {
        var platformInput = row.querySelector('.social-picker__platform-input');
        var urlInput = row.querySelector('.social-picker__url');
        if (platformInput) {
          platformInput.name = 'social_link_' + index + '_platform';
          platformInput.value = 'other';
        }
        if (urlInput) urlInput.name = 'social_link_' + index + '_url';
        index += 1;
      });
    }

    function updateIconState(platform, isActive) {
      var iconBtn = root.querySelector('[data-social-icon][data-platform="' + platform + '"]');
      if (!iconBtn) return;
      iconBtn.classList.toggle('social-picker__icon-btn--active', isActive);
      iconBtn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    }

    function showUrlRow(platform, focusInput) {
      var row = mainUrlsWrap.querySelector('[data-social-url-row][data-platform="' + platform + '"]');
      if (!row) return;
      row.classList.remove('social-picker__url-row--hidden');
      updateIconState(platform, true);
      if (focusInput) {
        var input = row.querySelector('.social-picker__url');
        if (input) input.focus();
      }
    }

    function hideUrlRow(platform) {
      var row = mainUrlsWrap.querySelector('[data-social-url-row][data-platform="' + platform + '"]');
      if (!row) return;
      var input = row.querySelector('.social-picker__url');
      if (input) input.value = '';
      row.classList.add('social-picker__url-row--hidden');
      updateIconState(platform, false);
    }

    function ensureOtherSection() {
      if (otherWrap) return otherWrap;
      otherWrap = document.createElement('div');
      otherWrap.className = 'social-picker__other';
      otherWrap.setAttribute('data-social-other', '');

      var label = document.createElement('span');
      label.className = 'social-picker__other-label';
      label.textContent = 'Другое';

      otherRowsWrap = document.createElement('div');
      otherRowsWrap.className = 'social-picker__other-rows';
      otherRowsWrap.setAttribute('data-social-other-rows', '');

      otherWrap.appendChild(label);
      otherWrap.appendChild(otherRowsWrap);
      root.insertBefore(otherWrap, addOtherBtn);
      return otherWrap;
    }

    function updateAddOtherButton() {
      if (!addOtherBtn) return;
      var otherRows = getOtherRows();
      var hasEmptyOther = false;
      otherRows.forEach(function (row) {
        var input = row.querySelector('.social-picker__url');
        if (input && !input.value.trim()) hasEmptyOther = true;
      });
      if (otherWrap && otherRows.length) {
        addOtherBtn.hidden = true;
        return;
      }
      addOtherBtn.hidden = getTotalLinkCount() >= maxLinks || hasEmptyOther;
    }

    function bindMainUrlRow(row) {
      var platform = row.getAttribute('data-platform');
      var urlInput = row.querySelector('.social-picker__url');
      var removeBtn = row.querySelector('.social-picker__remove');

      urlInput.addEventListener('input', function () {
        var hasUrl = !!urlInput.value.trim();
        updateIconState(platform, hasUrl || !row.classList.contains('social-picker__url-row--hidden'));
        updateAddOtherButton();
      });

      if (removeBtn) {
        removeBtn.addEventListener('click', function () {
          hideUrlRow(platform);
          updateAddOtherButton();
        });
      }
    }

    function bindOtherRow(row) {
      var urlInput = row.querySelector('.social-picker__url');
      var removeBtn = row.querySelector('.social-picker__remove');

      urlInput.addEventListener('input', updateAddOtherButton);

      if (removeBtn) {
        removeBtn.addEventListener('click', function () {
          if (getOtherRows().length === 1) {
            urlInput.value = '';
            if (otherWrap) otherWrap.remove();
            otherWrap = null;
            otherRowsWrap = null;
            assignOtherFieldNames();
            updateAddOtherButton();
            if (addOtherBtn) addOtherBtn.hidden = false;
            return;
          }
          row.remove();
          assignOtherFieldNames();
          updateAddOtherButton();
        });
      }
    }

    function addOtherRow(focusInput) {
      if (getTotalLinkCount() >= maxLinks) return;
      ensureOtherSection();
      var clone = otherTemplate.content.cloneNode(true);
      otherRowsWrap.appendChild(clone);
      var newRow = otherRowsWrap.lastElementChild;
      assignOtherFieldNames();
      bindOtherRow(newRow);
      updateAddOtherButton();
      if (focusInput !== false) {
        newRow.querySelector('.social-picker__url').focus();
      }
    }

    iconButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var platform = btn.getAttribute('data-platform');
        var row = mainUrlsWrap.querySelector('[data-social-url-row][data-platform="' + platform + '"]');
        if (!row) return;
        if (row.classList.contains('social-picker__url-row--hidden')) {
          showUrlRow(platform, true);
        } else {
          row.querySelector('.social-picker__url').focus();
        }
        updateAddOtherButton();
      });
    });

    if (addOtherBtn) {
      addOtherBtn.addEventListener('click', function () {
        addOtherRow(true);
        addOtherBtn.hidden = true;
      });
    }

    getMainUrlRows().forEach(bindMainUrlRow);
    getOtherRows().forEach(bindOtherRow);
    assignOtherFieldNames();
    updateAddOtherButton();
  }

  document.querySelectorAll('[data-social-picker]').forEach(initSocialPicker);
})();
