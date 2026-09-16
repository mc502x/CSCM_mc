/* Vanilla JS only, no framework, no CDN (docs/11-security-architecture.md §12). */

/* Dependent Functional Subgroup dropdown: fetches from the read-only lookup
 * API (GET, no CSRF needed) whenever the Functional System Group changes. */
function initSubgroupDependency(groupSelectId, subgroupSelectId) {
  var groupSelect = document.getElementById(groupSelectId);
  var subgroupSelect = document.getElementById(subgroupSelectId);
  if (!groupSelect || !subgroupSelect) return;

  function loadSubgroups(preselect) {
    var groupCode = groupSelect.value;
    subgroupSelect.innerHTML = '<option value="">(none)</option>';
    if (!groupCode) return;
    fetch('/api/v1/lookups/functional-subgroups?functional_system_group=' + encodeURIComponent(groupCode))
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (items) {
        items.forEach(function (item) {
          var opt = document.createElement('option');
          opt.value = item.code;
          opt.textContent = item.label + ' (' + item.range_start + '-' + item.range_end + ')';
          if (preselect && preselect === item.code) opt.selected = true;
          subgroupSelect.appendChild(opt);
        });
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
