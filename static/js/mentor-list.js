(function () {
  const form = document.getElementById('mentors-filter-form');
  if (!form) return;

  const tagsWrap = form.querySelector('[data-filter-tags]');
  const skillSearch = form.querySelector('[data-skill-search]');
  const sortSelect = document.getElementById('mentors-sort');
  const expandBtn = form.querySelector('[data-tags-expand]');
  const ratingRange = form.querySelector('[data-rating-range]');

  if (skillSearch && tagsWrap) {
    skillSearch.addEventListener('input', () => {
      const query = skillSearch.value.trim().toLowerCase();
      tagsWrap.querySelectorAll('.mentors-filter__tag').forEach((tag) => {
        const label = tag.textContent.trim().toLowerCase();
        tag.hidden = query && !label.includes(query);
      });
    });
  }

  if (expandBtn && tagsWrap) {
    const expandLabel = expandBtn.querySelector('[data-tags-expand-label]');
    expandBtn.addEventListener('click', () => {
      const expanded = expandBtn.getAttribute('aria-expanded') === 'true';
      expandBtn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      tagsWrap.classList.toggle('mentors-filter__tags--collapsed', expanded);
      tagsWrap.classList.toggle('mentors-filter__tags--expanded', !expanded);
      if (expandLabel) {
        expandLabel.textContent = expanded
          ? 'Развернуть все направления'
          : 'Свернуть направления';
      }
    });
  }

  if (ratingRange) {
    const minInput = ratingRange.querySelector('[data-rating-min]');
    const maxInput = ratingRange.querySelector('[data-rating-max]');
    const fill = ratingRange.querySelector('[data-rating-fill]');
    const minLabel = ratingRange.querySelector('[data-rating-min-label]');
    const maxLabel = ratingRange.querySelector('[data-rating-max-label]');
    const minBound = 0;
    const maxBound = 5;

    function syncZIndex() {
      const minVal = parseInt(minInput.value, 10);
      const maxVal = parseInt(maxInput.value, 10);
      if (minInput === document.activeElement) {
        minInput.style.zIndex = 5;
        maxInput.style.zIndex = 4;
      } else if (maxInput === document.activeElement) {
        maxInput.style.zIndex = 5;
        minInput.style.zIndex = 3;
      } else if (minVal === maxVal) {
        minInput.style.zIndex = 3;
        maxInput.style.zIndex = 5;
      } else {
        minInput.style.zIndex = 3;
        maxInput.style.zIndex = 4;
      }
    }

    function updateRatingRange() {
      let minVal = parseInt(minInput.value, 10);
      let maxVal = parseInt(maxInput.value, 10);

      if (minVal > maxVal) {
        if (document.activeElement === minInput) {
          maxInput.value = String(minVal);
          maxVal = minVal;
        } else {
          minInput.value = String(maxVal);
          minVal = maxVal;
        }
      }

      const span = maxBound - minBound;
      const minPercent = ((minVal - minBound) / span) * 100;
      const maxPercent = ((maxVal - minBound) / span) * 100;

      fill.style.left = minPercent + '%';
      fill.style.width = (maxPercent - minPercent) + '%';

      if (minLabel) minLabel.textContent = String(minVal);
      if (maxLabel) maxLabel.textContent = String(maxVal);

      syncZIndex();
    }

    minInput.addEventListener('input', updateRatingRange);
    maxInput.addEventListener('input', updateRatingRange);
    minInput.addEventListener('change', updateRatingRange);
    maxInput.addEventListener('change', updateRatingRange);
    minInput.addEventListener('focus', syncZIndex);
    maxInput.addEventListener('focus', syncZIndex);

    updateRatingRange();
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      const hidden = form.querySelector('input[name="sort"]');
      if (hidden) {
        hidden.value = sortSelect.value;
        form.requestSubmit();
      }
    });
  }

  document.querySelectorAll('[data-bio-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const bio = btn.previousElementSibling;
      if (!bio) return;
      const collapsed = bio.classList.toggle('mentor-catalog-card__bio--collapsed');
      btn.textContent = collapsed ? 'Развернуть полное описание' : 'Свернуть описание';
    });
  });
})();
