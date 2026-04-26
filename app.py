"""
app.py  –  PDF Address Extractor  |  Web Interface
Run:  python app.py
Then open:  http://localhost:5000
"""

import json
import os
import csv
import io
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_file
import tempfile

from extractor import extract

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PDF Address Extractor</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #0b0c0f;
    --bg2:      #13151a;
    --bg3:      #1c1f27;
    --border:   #2a2d38;
    --accent:   #4fffb0;
    --accent2:  #00c9ff;
    --muted:    #6b7280;
    --text:     #e8eaf0;
    --danger:   #ff5e5e;
    --warn:     #f5a623;
    --radius:   10px;
    --mono:     'DM Mono', monospace;
    --sans:     'Syne', sans-serif;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    min-height: 100vh;
    display: grid;
    grid-template-rows: auto 1fr auto;
  }

  /* ── Header ── */
  header {
    border-bottom: 1px solid var(--border);
    padding: 20px 40px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .logo {
    width: 36px; height: 36px;
    background: var(--accent);
    border-radius: 8px;
    display: grid; place-items: center;
    flex-shrink: 0;
  }
  .logo svg { width: 20px; height: 20px; }
  header h1 { font-size: 18px; font-weight: 800; letter-spacing: -.3px; }
  header p  { font-size: 13px; color: var(--muted); margin-top: 1px; font-family: var(--mono); }
  .badge {
    margin-left: auto;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 11px;
    font-family: var(--mono);
    color: var(--accent);
  }

  /* ── Main layout ── */
  main {
    padding: 40px;
    display: grid;
    grid-template-columns: 360px 1fr;
    gap: 24px;
    align-items: start;
    max-width: 1280px;
    width: 100%;
    margin: 0 auto;
  }

  /* ── Upload panel ── */
  .panel {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .panel-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    font-size: 11px;
    font-family: var(--mono);
    color: var(--muted);
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .panel-body { padding: 20px; }

  /* drop zone */
  .dropzone {
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    padding: 40px 20px;
    text-align: center;
    cursor: pointer;
    transition: border-color .2s, background .2s;
    position: relative;
  }
  .dropzone:hover, .dropzone.drag { border-color: var(--accent); background: rgba(79,255,176,.04); }
  .dropzone input[type=file] {
    position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }
  .dropzone-icon { font-size: 32px; margin-bottom: 10px; }
  .dropzone h3 { font-size: 14px; font-weight: 700; margin-bottom: 6px; }
  .dropzone p  { font-size: 12px; color: var(--muted); font-family: var(--mono); }
  .file-selected {
    margin-top: 14px;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 12px;
    font-family: var(--mono);
    color: var(--accent);
    display: none;
  }

  /* filters */
  .filter-row {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .filter-row label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; font-family: var(--mono); display: block; margin-bottom: 6px; }
  select, .select-wrap select {
    width: 100%;
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 6px;
    padding: 9px 12px;
    font-size: 13px;
    font-family: var(--mono);
    appearance: none;
    cursor: pointer;
    outline: none;
    transition: border-color .2s;
  }
  select:focus { border-color: var(--accent); }

  /* extract button */
  .btn-extract {
    margin-top: 20px;
    width: 100%;
    padding: 13px;
    background: var(--accent);
    color: #0b0c0f;
    font-family: var(--sans);
    font-weight: 800;
    font-size: 14px;
    border: none;
    border-radius: var(--radius);
    cursor: pointer;
    letter-spacing: .02em;
    transition: opacity .2s, transform .1s;
    display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .btn-extract:hover { opacity: .9; }
  .btn-extract:active { transform: scale(.98); }
  .btn-extract:disabled { opacity: .4; cursor: not-allowed; }

  /* stats bar */
  .stats-bar {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: var(--border);
    border-radius: 8px;
    overflow: hidden;
    margin-top: 20px;
  }
  .stat {
    background: var(--bg3);
    padding: 14px;
    text-align: center;
  }
  .stat-value { font-size: 22px; font-weight: 800; color: var(--accent); }
  .stat-label { font-size: 10px; color: var(--muted); font-family: var(--mono); text-transform: uppercase; margin-top: 2px; }

  /* ── Results panel ── */
  .results-panel {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    min-height: 420px;
    display: flex;
    flex-direction: column;
  }
  .results-header {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .results-title {
    font-size: 11px;
    font-family: var(--mono);
    color: var(--muted);
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .results-count {
    background: var(--accent);
    color: #0b0c0f;
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 20px;
  }
  .export-btns { margin-left: auto; display: flex; gap: 8px; }
  .btn-sm {
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-family: var(--mono);
    font-weight: 500;
    border: 1px solid var(--border);
    background: var(--bg3);
    color: var(--text);
    cursor: pointer;
    transition: border-color .2s, color .2s;
    text-decoration: none;
    display: inline-flex; align-items: center; gap: 5px;
  }
  .btn-sm:hover { border-color: var(--accent2); color: var(--accent2); }

  /* table */
  .table-wrap { overflow-x: auto; flex: 1; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--mono);
    font-size: 12px;
  }
  thead th {
    padding: 10px 16px;
    text-align: left;
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .08em;
    background: var(--bg3);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    font-weight: 500;
  }
  tbody tr { border-bottom: 1px solid var(--border); transition: background .15s; }
  tbody tr:hover { background: var(--bg3); }
  tbody td { padding: 11px 16px; vertical-align: middle; }
  .td-street { color: var(--text); font-weight: 500; }
  .td-city, .td-state, .td-zip, .td-page { color: var(--muted); }
  .conf-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 8px; border-radius: 20px; font-size: 10px; font-weight: 500;
  }
  .conf-high   { background: rgba(79,255,176,.12);  color: var(--accent); }
  .conf-medium { background: rgba(245,166,35,.12);  color: var(--warn); }
  .conf-low    { background: rgba(255,94,94,.12);   color: var(--danger); }
  .dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
  .dot-high   { background: var(--accent); }
  .dot-medium { background: var(--warn); }
  .dot-low    { background: var(--danger); }

  /* empty / loading states */
  .empty-state {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 12px; padding: 60px 20px; color: var(--muted);
    font-family: var(--mono); font-size: 13px;
  }
  .empty-state-icon { font-size: 40px; opacity: .5; }
  .spinner {
    width: 28px; height: 28px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin .7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .error-msg {
    background: rgba(255,94,94,.1);
    border: 1px solid rgba(255,94,94,.3);
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 13px;
    font-family: var(--mono);
    color: var(--danger);
    margin: 20px;
  }

  /* footer */
  footer {
    padding: 16px 40px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    font-family: var(--mono);
    color: var(--muted);
    display: flex; gap: 20px;
  }

  /* row animation */
  tbody tr { animation: rowIn .25s ease both; }
  @keyframes rowIn { from { opacity: 0; transform: translateY(4px); } }
</style>
</head>
<body>

<header>
  <div class="logo">
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="2" width="10" height="13" rx="1.5" stroke="#0b0c0f" stroke-width="1.5"/>
      <path d="M7 6h4M7 9h4M7 12h2" stroke="#0b0c0f" stroke-width="1.5" stroke-linecap="round"/>
      <circle cx="15" cy="15" r="3.5" fill="#0b0c0f" stroke="#0b0c0f"/>
      <path d="M13.5 15l1 1 2-2" stroke="var(--accent)" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <div>
    <h1>PDF Address Extractor</h1>
    <p>Extract structured addresses from any PDF</p>
  </div>
  <span class="badge">v1.0.0</span>
</header>

<main>

  <!-- Left: Upload + controls -->
  <aside>
    <div class="panel">
      <div class="panel-header">01 — Upload</div>
      <div class="panel-body">
        <div class="dropzone" id="dropzone">
          <input type="file" id="fileInput" accept=".pdf">
          <div class="dropzone-icon">📄</div>
          <h3>Drop your PDF here</h3>
          <p>or click to browse</p>
        </div>
        <div class="file-selected" id="fileSelected"></div>

        <div class="filter-row">
          <div>
            <label>Confidence filter</label>
            <select id="confFilter">
              <option value="all">All results</option>
              <option value="high">High only (full address)</option>
              <option value="medium">High + Medium</option>
            </select>
          </div>
        </div>

        <button class="btn-extract" id="extractBtn" disabled onclick="runExtract()">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 2v9M4 7l4 4 4-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 13h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
          Extract Addresses
        </button>

        <div class="stats-bar" id="statsBar" style="display:none">
          <div class="stat"><div class="stat-value" id="statTotal">0</div><div class="stat-label">Found</div></div>
          <div class="stat"><div class="stat-value" id="statHigh">0</div><div class="stat-label">High conf.</div></div>
          <div class="stat"><div class="stat-value" id="statPages">0</div><div class="stat-label">Pages</div></div>
        </div>
      </div>
    </div>
  </aside>

  <!-- Right: Results table -->
  <section class="results-panel" id="resultsPanel">
    <div class="results-header">
      <span class="results-title">02 — Results</span>
      <span class="results-count" id="resultsCount" style="display:none">0</span>
      <div class="export-btns" id="exportBtns" style="display:none">
        <button class="btn-sm" onclick="exportCSV()">⬇ CSV</button>
        <button class="btn-sm" onclick="exportJSON()">⬇ JSON</button>
      </div>
    </div>

    <div class="empty-state" id="emptyState">
      <div class="empty-state-icon">🗂️</div>
      <span>Upload a PDF to get started</span>
    </div>
    <div class="empty-state" id="loadingState" style="display:none">
      <div class="spinner"></div>
      <span>Extracting addresses…</span>
    </div>
    <div class="error-msg" id="errorMsg" style="display:none"></div>

    <div class="table-wrap" id="tableWrap" style="display:none">
      <table>
        <thead>
          <tr>
            <th>Street</th>
            <th>City</th>
            <th>State</th>
            <th>ZIP</th>
            <th>Page</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </section>

</main>

<footer>
  <span>pdf-address-extractor</span>
  <span>·</span>
  <span>pdfplumber + pypdf</span>
  <span>·</span>
  <span id="footerStats"></span>
</footer>

<script>
  let allResults = [];

  // ── Drag & drop ──────────────────────────────────────────────────────────
  const dz = document.getElementById('dropzone');
  const fi = document.getElementById('fileInput');

  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
  dz.addEventListener('drop', e => {
    e.preventDefault(); dz.classList.remove('drag');
    const f = e.dataTransfer.files[0];
    if (f && f.type === 'application/pdf') setFile(f);
  });
  fi.addEventListener('change', () => { if (fi.files[0]) setFile(fi.files[0]); });

  function setFile(file) {
    const sel = document.getElementById('fileSelected');
    sel.style.display = 'block';
    sel.textContent = `📎 ${file.name}  (${(file.size/1024).toFixed(1)} KB)`;
    document.getElementById('extractBtn').disabled = false;
  }

  // ── Extract ──────────────────────────────────────────────────────────────
  async function runExtract() {
    const file = fi.files[0];
    if (!file) return;

    setState('loading');

    const fd = new FormData();
    fd.append('file', file);
    fd.append('confidence', document.getElementById('confFilter').value);

    try {
      const res = await fetch('/extract', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Server error');
      allResults = data.addresses;
      renderTable(allResults, data.pages);
    } catch (err) {
      setState('error', err.message);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────
  function renderTable(addresses, pages) {
    const body = document.getElementById('tableBody');
    body.innerHTML = '';

    addresses.forEach((a, i) => {
      const tr = document.createElement('tr');
      tr.style.animationDelay = `${i * 18}ms`;
      tr.innerHTML = `
        <td class="td-street">${esc(a.street)}</td>
        <td class="td-city">${esc(a.city) || '—'}</td>
        <td class="td-state">${esc(a.state) || '—'}</td>
        <td class="td-zip">${esc(a.zip_code) || '—'}</td>
        <td class="td-page">${a.page}</td>
        <td><span class="conf-badge conf-${a.confidence}">
          <span class="dot dot-${a.confidence}"></span>${a.confidence}
        </span></td>`;
      body.appendChild(tr);
    });

    const high = addresses.filter(a => a.confidence === 'high').length;
    document.getElementById('statTotal').textContent = addresses.length;
    document.getElementById('statHigh').textContent  = high;
    document.getElementById('statPages').textContent = pages;
    document.getElementById('statsBar').style.display = 'grid';
    document.getElementById('resultsCount').textContent = `${addresses.length} found`;
    document.getElementById('resultsCount').style.display = '';
    document.getElementById('exportBtns').style.display = '';
    document.getElementById('footerStats').textContent =
      `${addresses.length} addresses · ${high} high confidence · ${pages} pages scanned`;

    setState('results');
  }

  function setState(s, msg) {
    document.getElementById('emptyState').style.display   = s === 'empty'   ? '' : 'none';
    document.getElementById('loadingState').style.display = s === 'loading'  ? '' : 'none';
    document.getElementById('tableWrap').style.display    = s === 'results'  ? '' : 'none';
    const err = document.getElementById('errorMsg');
    err.style.display = s === 'error' ? '' : 'none';
    if (s === 'error') err.textContent = '⚠ ' + msg;
  }

  // ── Export ───────────────────────────────────────────────────────────────
  function exportCSV() {
    if (!allResults.length) return;
    const headers = ['street','city','state','zip_code','full','page','confidence'];
    const rows = [headers.join(','),
      ...allResults.map(a => headers.map(h => `"${(a[h]||'').toString().replace(/"/g,'""')}"`).join(','))
    ];
    download(rows.join('\n'), 'addresses.csv', 'text/csv');
  }

  function exportJSON() {
    if (!allResults.length) return;
    download(JSON.stringify(allResults, null, 2), 'addresses.json', 'application/json');
  }

  function download(content, name, type) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([content], { type }));
    a.download = name; a.click();
  }

  function esc(s) {
    return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/extract", methods=["POST"])
def extract_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    confidence_filter = request.form.get("confidence", "all")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        addresses = extract(tmp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)

    # Confidence filtering
    level_map = {
        "high":   {"high"},
        "medium": {"high", "medium"},
        "all":    {"high", "medium", "low"},
    }
    keep = level_map.get(confidence_filter, {"high", "medium", "low"})
    filtered = [a for a in addresses if a.confidence in keep]

    # Count pages
    pages = len(set(a.page for a in addresses)) if addresses else 0

    return jsonify({
        "addresses": [a.to_dict() for a in filtered],
        "total":     len(addresses),
        "filtered":  len(filtered),
        "pages":     pages,
    })


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  PDF Address Extractor  –  Web Interface")
    print("=" * 50)
    print("  Open in your browser:")
    print("  → http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=False, port=5000)
