# ruff: noqa: E501  (user-facing help text and an embedded HTML page)
"""Offline field-lookup bundle (I-24): one self-contained HTML file with the Release's
codes embedded as JSON and a small search box, for service technicians at the turbine
without connectivity. It needs no server and loads nothing from the network; the JSON and
script are inline, and the file's SHA-256 is listed in the manifest that ships with it."""

import json

_COLUMNS = (
    ("status_code_identifier", "Status code"),
    ("title", "Title"),
    ("description", "Description"),
    ("status_category", "Category"),
    ("alarm_flag", "Alarm"),
    ("set_delay", "Set delay"),
    ("reset_delay", "Reset delay"),
    ("affected_component", "Component"),
    ("remedy_text", "Remedy"),
    ("turbine_platforms", "Platforms"),
)

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ - offline lookup</title>
<style>
body{font:15px/1.4 system-ui,Segoe UI,Arial,sans-serif;margin:0;color:#1a1a1a;background:#fff}
header{padding:12px 16px;background:#14304a;color:#fff}
header h1{margin:0;font-size:18px}
header p{margin:2px 0 0;font-size:12px;opacity:.85}
main{padding:12px 16px}
#q{width:100%;max-width:560px;padding:10px;font-size:16px;border:1px solid #888;border-radius:4px}
#count{margin:8px 0;color:#555;font-size:13px}
table{border-collapse:collapse;width:100%}
th,td{border:1px solid #ccc;padding:6px 8px;text-align:left;vertical-align:top;font-size:13px}
th{background:#eef1f5;position:sticky;top:0}
.ERROR{color:#a40000;font-weight:600}.WARNING{color:#8a5a00;font-weight:600}.INFO{color:#1d5a8a}
footer{padding:12px 16px;font-size:11px;color:#666}
</style>
</head>
<body>
<header><h1>__TITLE__</h1><p>__SUBTITLE__</p></header>
<main>
<label for="q" class="muted">Search identifier, title, description, component or remedy</label><br>
<input id="q" type="search" placeholder="e.g. 01042, converter, grid undervoltage" autocomplete="off">
<div id="count"></div>
<table><thead><tr>__HEADERS__</tr></thead><tbody id="rows"></tbody></table>
</main>
<footer>Read-only copy generated __GENERATED__. Content digest (SHA-256 of the data): __DIGEST__.
Verify the file against MANIFEST.json before relying on it.</footer>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var rows = JSON.parse(document.getElementById('data').textContent);
  var fields = __FIELDS__;
  var body = document.getElementById('rows');
  var count = document.getElementById('count');
  var box = document.getElementById('q');
  function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
  function haystack(r) { return fields.map(function (f) { return r[f] == null ? '' : String(r[f]); }).join(' ').toLowerCase(); }
  var index = rows.map(haystack);
  function render() {
    var terms = box.value.toLowerCase().split(/\\s+/).filter(Boolean);
    var shown = 0, html = '';
    for (var i = 0; i < rows.length && shown < 300; i++) {
      var ok = terms.every(function (t) { return index[i].indexOf(t) !== -1; });
      if (!ok) continue;
      shown++;
      html += '<tr>' + fields.map(function (f) {
        var v = rows[i][f];
        if (typeof v === 'boolean') v = v ? 'Yes' : 'No';
        var cls = f === 'status_category' ? ' class="' + esc(v) + '"' : '';
        return '<td' + cls + '>' + esc(v) + '</td>';
      }).join('') + '</tr>';
    }
    body.innerHTML = html;
    count.textContent = shown + (shown === 300 ? '+' : '') + ' of ' + rows.length + ' codes';
  }
  box.addEventListener('input', render);
  render();
})();
</script>
</body>
</html>
"""


def _escape_json_for_html(payload: str) -> str:
    """Keep the JSON from closing its own <script> element or being read as markup."""
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def _html_text(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def build_offline_bundle(
    rows: list[dict], *, title: str, subtitle: str, generated: str, digest: str
) -> bytes:
    fields = [f for f, _label in _COLUMNS if rows and f in rows[0]] or [f for f, _ in _COLUMNS]
    labels = dict(_COLUMNS)
    data = [{f: row.get(f) for f in fields} for row in rows]
    page = (
        _PAGE.replace("__TITLE__", _html_text(title))
        .replace("__SUBTITLE__", _html_text(subtitle))
        .replace("__HEADERS__", "".join(f"<th>{_html_text(labels[f])}</th>" for f in fields))
        .replace("__GENERATED__", _html_text(generated))
        .replace("__DIGEST__", _html_text(digest))
        .replace("__FIELDS__", json.dumps(fields))
        .replace("__DATA__", _escape_json_for_html(json.dumps(data, ensure_ascii=False)))
    )
    return page.encode("utf-8")
