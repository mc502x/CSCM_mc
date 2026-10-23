/* Vanilla JS only, no framework, no CDN (docs/11-security-architecture.md §12). */

/* Dependent Functional Subgroup dropdown: fetches from the read-only lookup
 * API (GET, no CSRF needed) whenever the Functional System Group changes.
 * v3: Functional Subgroup is mandatory (never optional), and both the group
 * and subgroup are identified by their surrogate id, not their `code` —
 * `code` is no longer unique on its own (see
 * app/services/lookup_service.py). Each option's description (NFR-007b) is
 * shown as secondary text via a <small> node inside the option's label
 * where supported, and always via the title tooltip. */
function initSubgroupDependency(groupSelectId, subgroupSelectId) {
  var groupSelect = document.getElementById(groupSelectId);
  var subgroupSelect = document.getElementById(subgroupSelectId);
  if (!groupSelect || !subgroupSelect) return;

  function loadSubgroups(preselect) {
    var groupId = groupSelect.value;
    subgroupSelect.innerHTML = '';
    subgroupSelect.disabled = true;
    if (!groupId) {
      subgroupSelect.innerHTML = '<option value="">Select a Functional System Group first</option>';
      return;
    }
    subgroupSelect.innerHTML = '<option value="">(select)</option>';
    fetch('/api/v1/lookups/functional-subgroups?functional_system_group=' + encodeURIComponent(groupId))
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (items) {
        subgroupSelect.disabled = false;
        items.forEach(function (item) {
          var opt = document.createElement('option');
          opt.value = item.id;
          opt.textContent = item.label + ' (' + item.range_start + '-' + item.range_end + ')';
          if (item.description) opt.title = item.description;
          opt.setAttribute('data-description', item.description || item.label || '');
          if (preselect && String(preselect) === String(item.id)) opt.selected = true;
          subgroupSelect.appendChild(opt);
        });
        updateSelectHelp(subgroupSelect);
      });
  }

  var initialSubgroup = subgroupSelect.getAttribute('data-selected') || '';
  if (groupSelect.value) loadSubgroups(initialSubgroup);
  groupSelect.addEventListener('change', function () { loadSubgroups(null); });
}

/* Typed-confirmation guard: disables a submit button until the user types
 * the expected text into a companion input (sandbox delete, release
 * publish — docs/10-ui-ux-specification.md §9). */
function initTypedConfirm(inputId, buttonId, expectedText) {
  var input = document.getElementById(inputId);
  var button = document.getElementById(buttonId);
  if (!input || !button) return;
  button.disabled = true;
  input.addEventListener('input', function () {
    button.disabled = input.value !== expectedText;
  });
}

/* Declarative hooks (data-* attributes) so templates carry no inline
 * <script> or on*= handlers — required by the strict script-src 'self'
 * Content-Security-Policy (app/security_headers.py, SEC-025). */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-subgroup-dependency]').forEach(function (el) {
    var ids = el.getAttribute('data-subgroup-dependency').split(',');
    initSubgroupDependency(ids[0], ids[1]);
  });
  document.querySelectorAll('[data-typed-confirm]').forEach(function (el) {
    initTypedConfirm(el.id, el.getAttribute('data-typed-confirm'), el.getAttribute('data-expected'));
  });
  document.querySelectorAll('[data-autosubmit]').forEach(function (el) {
    el.addEventListener('change', function () { el.form.submit(); });
  });
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(form.getAttribute('data-confirm'))) e.preventDefault();
    });
  });
  document.querySelectorAll('tr[data-href]').forEach(function (row) {
    row.addEventListener('click', function () { window.location = row.getAttribute('data-href'); });
  });
  document.querySelectorAll('a[data-history-back]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); window.history.back(); });
  });
});

/* NFR-007b: show the selected option's description as inline help; falls
 * back to an explicit "not yet available" note rather than leaving the user
 * choosing between unexplained options. */
function updateSelectHelp(select) {
  var helpId = select.getAttribute('data-help');
  var help = helpId ? document.getElementById(helpId) : null;
  if (!help) return;
  var option = select.options[select.selectedIndex];
  if (!option || !option.value) { help.textContent = ''; return; }
  var text = option.getAttribute('data-description');
  help.textContent = text ? text : 'No description available yet \u2014 confirm with Controls Engineering.';
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('select[data-help]').forEach(function (select) {
    select.addEventListener('change', function () { updateSelectHelp(select); });
    updateSelectHelp(select);
  });
});

/* ------------------------------------------------------------------------
 * v4 behaviours (docs/21-improvement-ideas.md). Same rules as above: no inline
 * scripts, everything is wired from data-* attributes (strict CSP, SEC-025).
 * ---------------------------------------------------------------------- */

/* I-19: "StCd-01042 of 1000-1199 (158 numbers left)" under the identifier box when a
 * subgroup is chosen on the New Status Code form. */
function initCapacityHint(subgroupSelect) {
  var target = document.getElementById(subgroupSelect.getAttribute('data-capacity-hint'));
  var group = document.getElementById('functional_system_group');
  if (!target || !group) return;
  function show() {
    if (!group.value || !subgroupSelect.value) { target.textContent = ''; return; }
    fetch('/api/v1/status-codes/next-available?functional_system_group=' + encodeURIComponent(group.value) +
          '&functional_subgroup=' + encodeURIComponent(subgroupSelect.value))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.capacity) { target.textContent = data.message || ''; return; }
        var c = data.capacity;
        target.textContent = data.preview_identifier + ' of ' + c.range_start + '–' + c.range_end +
          ' (' + c.remaining + ' numbers left in this subgroup)';
        target.className = 'hint' + (c.remaining <= 20 ? ' sla sla--amber' : '');
      })
      .catch(function () { target.textContent = ''; });
  }
  subgroupSelect.addEventListener('change', show);
  show();
}

/* I-12: "did you mean to revise StCd-...?" while typing a new title. */
function initSimilarHint(input) {
  var target = document.getElementById(input.getAttribute('data-similar-hint'));
  var subgroup = document.getElementById('functional_subgroup');
  if (!target || !subgroup) return;
  var timer = null;
  function check() {
    if (!subgroup.value || input.value.trim().length < 4) { target.textContent = ''; return; }
    fetch('/api/v1/status-codes/similar?functional_subgroup=' + encodeURIComponent(subgroup.value) +
          '&title=' + encodeURIComponent(input.value.trim()))
      .then(function (r) { return r.ok ? r.json() : { items: [] }; })
      .then(function (data) {
        target.textContent = data.items.length
          ? 'Similar existing code: ' + data.items.map(function (i) {
              return (i.status_code_identifier || 'draft') + ' “' + i.title + '”';
            }).join('; ') + ' — did you mean to revise it?'
          : '';
      })
      .catch(function () { target.textContent = ''; });
  }
  input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(check, 350); });
}

/* I-26: the column chooser collects its checkboxes into one comma-separated value. */
function initColumnChooser(button) {
  var hidden = document.getElementById(button.getAttribute('data-collect-columns'));
  button.form.addEventListener('submit', function () {
    var chosen = [];
    button.form.querySelectorAll('.col-check').forEach(function (box) { if (box.checked) chosen.push(box.value); });
    hidden.value = chosen.join(',');
  });
}

/* I-32: poll a background import job until it finishes, then reload for the summary. */
function initImportProgress(box) {
  var url = box.getAttribute('data-progress-url');
  var bar = document.getElementById('import-progress-bar');
  var text = document.getElementById('import-progress-text');
  function poll() {
    fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (job) {
        if (bar) bar.value = job.progress_percent;
        if (text) text.textContent = job.processed_count + ' / ' + job.row_count;
        if (job.status === 'COMPLETE' || job.status === 'FAILED') { window.location.reload(); return; }
        setTimeout(poll, 1500);
      })
      .catch(function () { setTimeout(poll, 4000); });
  }
  setTimeout(poll, 1000);
}

/* S39: the header checkbox ticks or clears every enabled row checkbox of its class. */
function initCheckAll(box) {
  var cls = box.getAttribute('data-check-all');
  box.addEventListener('change', function () {
    document.querySelectorAll('input.' + cls + ':not(:disabled)').forEach(function (cb) { cb.checked = box.checked; });
  });
}

/* S39: a text box hides the rows of a table that do not contain what was typed. */
function initFilterRows(input) {
  var table = document.getElementById(input.getAttribute('data-filter-rows'));
  if (!table) return;
  input.addEventListener('input', function () {
    var needle = input.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(function (row) {
      row.hidden = needle !== '' && row.textContent.toLowerCase().indexOf(needle) === -1;
    });
  });
}

/* Translation review: set a verdict on every row of the page that has none yet. */
function initSetVerdict(button) {
  var table = document.getElementById(button.getAttribute('data-in'));
  var value = button.getAttribute('data-set-verdict');
  if (!table) return;
  button.addEventListener('click', function () {
    table.querySelectorAll('tbody tr').forEach(function (row) {
      var radios = row.querySelectorAll('input[type=radio]');
      if (!radios.length) return;
      var chosen = false;
      radios.forEach(function (r) { if (r.checked) chosen = true; });
      if (chosen) return;
      radios.forEach(function (r) { if (r.value === value && !r.disabled) r.checked = true; });
    });
  });
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('button[data-set-verdict]').forEach(initSetVerdict);
  document.querySelectorAll('input[data-check-all]').forEach(initCheckAll);
  document.querySelectorAll('input[data-filter-rows]').forEach(initFilterRows);
  document.querySelectorAll('select[data-capacity-hint]').forEach(initCapacityHint);
  document.querySelectorAll('input[data-similar-hint]').forEach(initSimilarHint);
  document.querySelectorAll('button[data-collect-columns]').forEach(initColumnChooser);
  document.querySelectorAll('[data-progress-url]').forEach(initImportProgress);
});
