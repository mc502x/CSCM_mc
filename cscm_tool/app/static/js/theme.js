/* Colour theme (docs/10-ui-ux-specification.md §13, FR-183): light, dark, or follow the operating
 * system. Loaded in the <head> without `defer`, so the page is coloured before it is first painted
 * (no flash of the wrong theme). The choice is kept on this device in localStorage; when storage is
 * blocked the page simply follows the system. Vanilla JS, no CDN (docs/11-security-architecture.md §12). */
(function () {
  var KEY = 'cscm-theme';
  var MODES = ['auto', 'light', 'dark'];
  var root = document.documentElement;
  var query = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function stored() {
    try {
      var value = window.localStorage.getItem(KEY);
      return MODES.indexOf(value) >= 0 ? value : 'auto';
    } catch (e) {
      return 'auto';
    }
  }

  function apply(mode) {
    var dark = mode === 'dark' || (mode === 'auto' && query && query.matches);
    root.setAttribute('data-theme', dark ? 'dark' : 'light');
    root.setAttribute('data-theme-mode', mode);
  }

  apply(stored());

  if (query) {
    var follow = function () { if (stored() === 'auto') apply('auto'); };
    if (query.addEventListener) query.addEventListener('change', follow);
    else if (query.addListener) query.addListener(follow);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('select[data-theme-select]').forEach(function (select) {
      select.value = stored();
      select.addEventListener('change', function () {
        var mode = MODES.indexOf(select.value) >= 0 ? select.value : 'auto';
        try { window.localStorage.setItem(KEY, mode); } catch (e) { /* storage blocked: this visit only */ }
        apply(mode);
        document.querySelectorAll('select[data-theme-select]').forEach(function (other) { other.value = mode; });
      });
    });
  });
})();
