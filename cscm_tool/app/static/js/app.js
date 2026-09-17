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
          if (preselect && String(preselect) === String(item.id)) opt.selected = true;
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
