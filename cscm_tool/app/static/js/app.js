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
