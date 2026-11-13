#!/usr/bin/env python3
"""Interfaz web local para extracción de metadatos de documentos."""

from __future__ import annotations

import argparse
import atexit
import html
import json
import logging
import secrets
import shutil
import tempfile
import threading
import time
import webbrowser
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .config import (
    APP_NAME,
    AUTHORS,
    MAX_CONCURRENT_REQUESTS,
    MAX_FILE_SIZE,
    MAX_REQUEST_SIZE,
    ORGANIZATION,
    REQUEST_TIMEOUT_SECONDS,
    __version__,
)
from .engine import SUPPORTED_EXTENSIONS, extract_file, is_supported_name
from .imagenes import COMPOUND_SUFFIXES, IMAGE_EXTENSIONS

LOGGER = logging.getLogger(__name__)

_TEMP_PREFIX = "extractor-metadatos-"
_TEMP_ROOT: Path | None = None


def _purge_stale_temp_dirs(max_age_seconds: int = 86400) -> None:
    """Elimina directorios temporales abandonados por ejecuciones anteriores."""
    cutoff = time.time() - max_age_seconds
    for candidate in Path(tempfile.gettempdir()).glob(f"{_TEMP_PREFIX}*"):
        try:
            if candidate.is_dir() and candidate.stat().st_mtime < cutoff:
                shutil.rmtree(candidate, ignore_errors=True)
        except OSError:
            continue


def _temp_root() -> Path:
    """Devuelve el directorio temporal de la ejecución, creándolo una sola vez."""
    global _TEMP_ROOT
    if _TEMP_ROOT is None:
        _purge_stale_temp_dirs()
        _TEMP_ROOT = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX))
        atexit.register(shutil.rmtree, _TEMP_ROOT, ignore_errors=True)
    return _TEMP_ROOT



HTML_PAGE = r"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__APP_NAME__</title>
  <style nonce="__NONCE__">
    :root {
      --bg: #f8fafc; --card: #ffffff; --border: #e2e8f0; --text: #0f172a; --muted: #64748b;
      --primary: #2563eb; --primary-hover: #1d4ed8; --danger: #ef4444; --success: #10b981;
      --radius: 12px; --shadow: 0 4px 12px rgba(15,23,42,0.05);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 24px 16px; min-width: 320px; line-height: 1.5; }
    .container { max-width: 1040px; margin: 0 auto; display: flex; flex-direction: column; gap: 18px; }
    header { text-align: center; }
    .badge-privacy { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 99px; background: #ecfdf5; color: #047857; font-size: .75rem; font-weight: 700; border: 1px solid #a7f3d0; margin-bottom: 8px; }
    .badge-privacy::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--success); box-shadow: 0 0 0 3px #d1fae5; }
    h1 { font-size: clamp(1.8rem, 4vw, 2.4rem); font-weight: 800; letter-spacing: -.03em; background: linear-gradient(135deg, #0f172a 40%, #2563eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    p.desc { color: var(--muted); font-size: .95rem; margin-top: 4px; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); padding: 20px; }
    .dropzone { border: 2px dashed #cbd5e1; border-radius: var(--radius); padding: 28px 16px; text-align: center; background: #f8fafc; transition: all .2s; cursor: pointer; display: grid; gap: 10px; justify-items: center; }
    .dropzone.dragover, .dropzone:hover { border-color: var(--primary); background: #eff6ff; box-shadow: 0 0 0 4px rgba(37,99,235,0.1); transform: scale(1.003); }
    .drop-icon { font-size: 2.2rem; display: inline-block; animation: bounce 2s infinite ease-in-out; }
    @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
    .btn-group { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
    .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 8px; border: 1px solid transparent; font-size: .88rem; font-weight: 600; cursor: pointer; transition: all .15s; text-decoration: none; font-family: inherit; }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover:not(:disabled) { background: var(--primary-hover); transform: translateY(-1px); }
    .btn-sec { background: #fff; border-color: var(--border); color: var(--text); }
    .btn-sec:hover:not(:disabled) { background: #f1f5f9; border-color: #cbd5e1; }
    .btn-danger { background: #fff; border-color: #fecaca; color: var(--danger); }
    .btn-danger:hover:not(:disabled) { background: #fef2f2; }
    .btn:disabled { opacity: .45; cursor: not-allowed; }
    .tags { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; font-size: .72rem; }
    .tag { padding: 2px 8px; border-radius: 6px; font-weight: 700; background: #f1f5f9; color: var(--muted); border: 1px solid #e2e8f0; }
    .progress-track { height: 6px; border-radius: 99px; background: #e2e8f0; overflow: hidden; margin-top: 10px; }
    .progress-bar { height: 100%; width: 0%; background: linear-gradient(90deg, #3b82f6, #6366f1); transition: width .2s; }
    .status-text { font-size: .85rem; color: var(--muted); font-weight: 500; margin-top: 6px; }
    .stats-bar { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; justify-content: space-between; font-size: .83rem; background: #f8fafc; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); }
    .stat-pill { display: inline-flex; align-items: center; gap: 5px; color: var(--muted); }
    .stat-pill b { color: var(--text); }
    .toolbar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; justify-content: space-between; margin-top: 14px; }
    .search-box { flex: 1 1 220px; max-width: 320px; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: .88rem; outline: none; }
    .search-box:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37,99,235,0.12); }
    .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; margin-top: 12px; }
    table { width: 100%; border-collapse: collapse; font-size: .85rem; text-align: left; }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
    th { background: #f8fafc; color: var(--muted); font-weight: 700; text-transform: uppercase; font-size: .72rem; letter-spacing: .05em; }
    tbody tr:hover { background: #f8fafc; }
    tbody tr:last-child td { border-bottom: none; }
    .num { font-variant-numeric: tabular-nums; white-space: nowrap; color: var(--muted); }
    .badge { padding: 2px 8px; border-radius: 6px; font-size: .72rem; font-weight: 800; text-transform: uppercase; display: inline-block; }
    .badge-pdf { background: #fee2e2; color: #991b1b; }
    .badge-docx, .badge-doc { background: #dbeafe; color: #1e40af; }
    .badge-xlsx, .badge-xls { background: #dcfce7; color: #166534; }
    .badge-txt { background: #f1f5f9; color: #475569; }
    .badge-img { background: #ede9fe; color: #5b21b6; }
    .badge-err { background: #fee2e2; color: #b91c1c; }
    .chips { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 4px; }
    .chip { background: #f1f5f9; color: #334155; padding: 2px 7px; border-radius: 5px; font-size: .74rem; border: 1px solid #e2e8f0; }
    .chip b { color: #0f172a; }
    .meta-details { margin-top: 6px; font-size: .8rem; }
    .meta-details summary { cursor: pointer; color: var(--primary); font-weight: 600; user-select: none; }
    .meta-details summary:hover { text-decoration: underline; }
    .json-wrap { position: relative; margin-top: 6px; }
    .json-pre { background: #0f172a; color: #f8fafc; padding: 10px; border-radius: 8px; font-size: .75rem; font-family: ui-monospace, Consolas, monospace; max-height: 220px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
    .btn-xs { position: absolute; top: 6px; right: 6px; padding: 2px 8px; font-size: .7rem; border-radius: 4px; background: #334155; color: #fff; border: none; cursor: pointer; }
    .btn-xs:hover { background: #475569; }
    .hash-line { display: flex; align-items: center; gap: 6px; margin-top: 6px; font-size: .74rem; flex-wrap: wrap; }
    .hash-label { color: var(--muted); font-weight: 700; letter-spacing: .03em; }
    .hash-value { font-family: ui-monospace, Consolas, monospace; background: #f1f5f9; border: 1px solid var(--border); border-radius: 5px; padding: 2px 6px; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; user-select: all; cursor: copy; }
    .hash-value:hover { background: #e2e8f0; }
    .btn-copy { padding: 2px 8px; font-size: .7rem; font-weight: 700; border-radius: 5px; background: #fff; border: 1px solid var(--border); color: var(--primary); cursor: pointer; font-family: inherit; }
    .btn-copy:hover { background: #eff6ff; border-color: var(--primary); }
    .btn-copy.copied { background: #ecfdf5; border-color: #a7f3d0; color: #047857; }
    .err-msg { color: var(--danger); font-size: .84rem; display: block; margin-top: 4px; }
    .empty-box { text-align: center; padding: 36px 16px; color: var(--muted); font-size: .9rem; }
    .footer { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px; margin-top: 4px; padding-top: 14px; border-top: 1px solid var(--border); color: var(--muted); font-size: .78rem; }
    .footer .brand { font-weight: 800; letter-spacing: .14em; color: var(--text); }
    .footer .sep { color: #cbd5e1; }
    .footer .authors { letter-spacing: .02em; }
    .hint { color: var(--muted); font-size: .85rem; margin-top: -6px; }
    .hidden-input { display: none; }
    .stat-ok { color: var(--success); }
    .stat-err { color: var(--danger); }
    .cell-name { max-width: 260px; overflow-wrap: anywhere; }
    .clipboard-helper { position: fixed; top: -1000px; opacity: 0; }
    @media (max-width: 640px) { .toolbar { flex-direction: column; align-items: stretch; } .search-box { max-width: 100%; } }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <span class="badge-privacy">Procesamiento 100% Local y Privado</span>
      <h1>__APP_NAME__</h1>
      <p class="desc">Analiza y exporta propiedades ocultas de documentos sin subirlos a internet.</p>
    </header>
    <main class="card">
      <div id="drop" class="dropzone">
        <span class="drop-icon">📂</span>
        <b>Arrastra y suelta tus archivos o carpetas aquí</b>
        <p class="hint">Hasta __MAX_MB__ MB por archivo</p>
        <div class="btn-group">
          <label class="btn btn-primary" for="files">Elegir Archivos</label>
          <label class="btn btn-sec" for="folder">Elegir Carpeta</label>
        </div>
        <div class="tags">__TAGS__</div>
      </div>
      <input id="files" type="file" multiple accept="__ACCEPT__" class="hidden-input">
      <input id="folder" type="file" multiple webkitdirectory directory class="hidden-input">
      <div id="progress-track" class="progress-track" hidden><div id="progress-bar" class="progress-bar"></div></div>
      <div id="status" class="status-text"></div>
    </main>
    <section class="card">
      <div class="stats-bar">
        <div class="stat-pill">Archivos: <b id="stat-total">0</b></div>
        <div class="stat-pill">Correctos: <b id="stat-ok" class="stat-ok">0</b></div>
        <div class="stat-pill">Errores: <b id="stat-err" class="stat-err">0</b></div>
        <div class="stat-pill">Tamaño Total: <b id="stat-size">0 B</b></div>
      </div>
      <div class="toolbar">
        <input id="search" class="search-box" type="search" placeholder="Buscar por nombre o metadato…" disabled>
        <div class="btn-group">
          <button id="btn-json" class="btn btn-sec" disabled>Exportar JSON</button>
          <button id="btn-csv" class="btn btn-sec" disabled>Exportar CSV</button>
          <button id="btn-clear" class="btn btn-danger" disabled>Limpiar</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Archivo</th><th>Formato</th><th>Tamaño</th><th>Metadatos y Estado</th></tr></thead>
          <tbody id="results"></tbody>
        </table>
        <div id="empty-state" class="empty-box">Aún no hay archivos analizados. Selecciona o arrastra documentos arriba.</div>
        <div id="no-matches" class="empty-box" hidden>No se encontraron resultados con ese criterio.</div>
      </div>
    </section>
    <footer class="footer">
      <span class="brand">__ORG__</span>
      <span class="sep">-</span>
      <span class="authors">__AUTHORS__</span>
    </footer>
  </div>
  <script nonce="__NONCE__">
    const ALLOWED = new Set(__EXTENSIONS__);
    const IMAGES = new Set(__IMAGE_EXTENSIONS__);
    const COMPOUND = __COMPOUND__;
    const MAX_BYTES = __MAX_BYTES__, MAX_MB = __MAX_MB__;
    const tbody = document.querySelector('#results');
    const $ = sel => document.querySelector(sel);
    let records = [], busy = false;

    // Comprueba el nombre completo, incluidos sufijos compuestos (.9.png, .nii.gz).
    const allowedName = name => {
      const lower = name.toLowerCase();
      return COMPOUND.some(suffix => lower.endsWith(suffix)) || ALLOWED.has('.' + lower.split('.').pop());
    };

    // Formatea bytes a unidades legibles (B, KB, MB).
    const fmtBytes = b => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;

    // Escapa caracteres especiales para HTML seguro.
    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

    // Devuelve el término de búsqueda activo ya normalizado.
    const term = () => $('#search').value.trim().toLowerCase();

    // Extrae etiquetas clave resumidas de los metadatos.
    function getChips(doc) {
      if (!doc || typeof doc !== 'object') return '';
      const map = { title: 'Título', creator: 'Creador', author: 'Autor', page_count: 'Páginas', sheet_count: 'Hojas', lines: 'Líneas', words: 'Palabras' };
      return Object.keys(map).filter(k => doc[k] != null && doc[k] !== '').map(k => `<span class="chip"><b>${map[k]}:</b> ${esc(doc[k])}</span>`).join('');
    }

    // Construye la fila de tabla derivada de un registro.
    function buildRow(rec) {
      const row = document.createElement('tr');
      const size = rec.filesystem?.size_bytes != null ? fmtBytes(rec.filesystem.size_bytes) : '—';
      const fmt = (rec.format || rec.filesystem?.extension?.replace('.', '') || '—').toLowerCase();
      const chips = getChips(rec.document);
      const hash = rec.filesystem?.sha256 || '';
      const badgeClass = IMAGES.has('.' + fmt) ? 'badge-img' : 'badge-' + fmt;
      const hashLine = hash
        ? `<div class="hash-line"><span class="hash-label">SHA-256</span><code class="hash-value" title="${esc(hash)}">${esc(hash)}</code><button class="btn-copy" type="button" data-action="copy-hash" data-sha="${esc(hash)}">Copiar</button></div>`
        : '';
      const jsonStr = JSON.stringify(rec.document || {}, null, 2);
      row.dataset.search = JSON.stringify(rec).toLowerCase();
      row.innerHTML = `
        <td class="cell-name"><b>${esc(rec.filesystem?.name || rec.file || 'Archivo')}</b></td>
        <td><span class="badge ${badgeClass}">${esc(fmt.toUpperCase())}</span></td>
        <td class="num">${size}</td>
        <td>
          ${rec.error ? `<span class="badge badge-err">Error</span><span class="err-msg">${esc(rec.error)}</span>` : `
            <div class="chips">${chips || '<span class="chip">Metadatos extraídos</span>'}</div>
            ${hashLine}
            <details class="meta-details">
              <summary>Ver JSON completo</summary>
              <div class="json-wrap">
                <button class="btn-xs" type="button" data-action="copy-json">Copiar</button>
                <pre class="json-pre">${esc(jsonStr)}</pre>
              </div>
            </details>`}
        </td>`;
      return row;
    }

    // Recalcula contadores y controles a partir del estado `records`.
    function refreshSummary() {
      const ok = records.filter(r => !r.error).length, err = records.length - ok;
      const bytes = records.reduce((acc, r) => acc + (r.filesystem?.size_bytes || 0), 0);
      $('#stat-total').textContent = records.length;
      $('#stat-ok').textContent = ok;
      $('#stat-err').textContent = err;
      $('#stat-size').textContent = fmtBytes(bytes);
      $('#empty-state').hidden = records.length > 0;
      ['#btn-json', '#btn-csv', '#btn-clear', '#search'].forEach(s => $(s).disabled = records.length === 0);
    }

    // Añade un registro al estado y su fila derivada al DOM.
    function addRecord(rec) {
      records.push(rec);
      const row = buildRow(rec), q = term();
      if (q && !row.dataset.search.includes(q)) row.hidden = true;
      else if (q) $('#no-matches').hidden = true;
      tbody.appendChild(row);
      refreshSummary();
    }

    // Construye un registro de error homogéneo para archivos descartados.
    const failRecord = (name, size, message) => ({
      file: name, format: name.split('.').pop().toLowerCase(),
      filesystem: { name, size_bytes: size }, document: {}, error: message
    });

    // Aplica el filtro de búsqueda sobre las filas ya renderizadas.
    function applyFilter() {
      const q = term();
      let shown = 0;
      for (const row of tbody.rows) {
        row.hidden = !!q && !row.dataset.search.includes(q);
        if (!row.hidden) shown++;
      }
      $('#no-matches').hidden = !q || shown > 0 || records.length === 0;
    }

    // Copia texto plano al portapapeles y confirma en el propio botón.
    async function copyText(txt, btn) {
      const ok = await writeClipboard(String(txt ?? ''));
      feedback(btn, ok ? '¡Copiado!' : 'No se pudo copiar');
    }

    // Escribe en el portapapeles, con respaldo para contextos sin API moderna.
    async function writeClipboard(txt) {
      try {
        await navigator.clipboard.writeText(txt);
        return true;
      } catch {
        const area = document.createElement('textarea');
        area.value = txt;
        area.className = 'clipboard-helper';
        document.body.appendChild(area);
        area.select();
        let done = false;
        try { done = document.execCommand('copy'); } catch { done = false; }
        area.remove();
        return done;
      }
    }

    // Muestra el resultado de la copia durante un instante.
    function feedback(btn, label) {
      if (!btn) return;
      if (!btn.dataset.label) btn.dataset.label = btn.textContent;
      btn.textContent = label;
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = btn.dataset.label; btn.classList.remove('copied'); }, 1400);
    }

    // Copia únicamente el SHA-256 del archivo, en texto plano.
    function copyHash(btn) { copyText(btn.dataset.sha, btn); }

    // Exporta registros en formato JSON o CSV descargable.
    function exportData(fmt) {
      if (!records.length) return;
      const q = v => `"${String(v ?? '').replaceAll('"', '""')}"`;
      const body = fmt === 'json'
        ? JSON.stringify(records, null, 2)
        : '\ufeff' + ['file,format,size_bytes,sha256,created,modified,document_metadata,error',
            ...records.map(r => [r.file, r.format, r.filesystem?.size_bytes, r.filesystem?.sha256, r.filesystem?.created, r.filesystem?.modified, JSON.stringify(r.document || {}), r.error].map(q).join(','))
          ].join('\r\n');
      const a = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(new Blob([body], { type: fmt === 'json' ? 'application/json' : 'text/csv;charset=utf-8' })),
        download: `metadatos.${fmt}`
      });
      a.click();
      URL.revokeObjectURL(a.href);
    }

    // Limpia todos los resultados y restablece la interfaz.
    function clearAll() {
      records = [];
      tbody.innerHTML = '';
      $('#search').value = '';
      $('#status').textContent = '';
      $('#progress-track').hidden = true;
      applyFilter();
      refreshSummary();
    }

    // Procesa la cola de archivos mediante la API local.
    async function processFiles(fileList) {
      const files = Array.from(fileList || []);
      if (busy || !files.length) return;
      busy = true;
      const bar = $('#progress-bar'), track = $('#progress-track'), status = $('#status');
      track.hidden = false;
      bar.style.width = '0%';
      let errs = 0;
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        status.textContent = `Procesando (${i + 1}/${files.length}): ${f.name}`;
        if (!allowedName(f.name)) {
          addRecord(failRecord(f.name, f.size, 'Extensión no admitida'));
          errs++;
        } else if (f.size > MAX_BYTES) {
          addRecord(failRecord(f.name, f.size, `Supera el límite de ${MAX_MB} MB`));
          errs++;
        } else {
          try {
            const fd = new FormData(); fd.append('file', f, f.name);
            const res = await fetch('/api/extract', { method: 'POST', body: fd });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
            addRecord(data);
            if (data.error) errs++;
          } catch (e) {
            addRecord(failRecord(f.name, f.size, e.message));
            errs++;
          }
        }
        bar.style.width = `${Math.round(((i + 1) / files.length) * 100)}%`;
      }
      applyFilter();
      status.textContent = `Finalizado: ${files.length - errs} exitoso(s), ${errs} con error.`;
      busy = false;
      $('#files').value = $('#folder').value = '';
    }

    // Configuración de escuchas y eventos de arrastre.
    const drop = $('#drop');
    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
    drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('dragover'); processFiles(e.dataTransfer.files); });
    $('#files').addEventListener('change', e => processFiles(e.target.files));
    $('#folder').addEventListener('change', e => processFiles(e.target.files));
    $('#search').addEventListener('input', applyFilter);
    $('#btn-json').addEventListener('click', () => exportData('json'));
    $('#btn-csv').addEventListener('click', () => exportData('csv'));
    $('#btn-clear').addEventListener('click', clearAll);
    tbody.addEventListener('click', event => {
      const btn = event.target.closest?.('button[data-action]');
      if (!btn) return;
      if (btn.dataset.action === 'copy-hash') copyText(btn.dataset.sha, btn);
      else if (btn.dataset.action === 'copy-json') copyText(btn.nextElementSibling?.textContent || '', btn);
    });
  </script>
</body>
</html>
"""


CSP_PAGE = (
    "default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
    "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'"
)
CSP_DEFAULT = "default-src 'none'; frame-ancestors 'none'"


def render_page(nonce: str) -> str:
    """Inyecta extensiones, límites, grupos de imagen y nonce CSP en la plantilla."""
    extensions = sorted(SUPPORTED_EXTENSIONS)
    images = sorted(IMAGE_EXTENSIONS)
    documents = [ext for ext in extensions if ext not in IMAGE_EXTENSIONS]
    tags = "".join(f'<span class="tag">{ext.lstrip(".").upper()}</span>' for ext in documents)
    tags += (
        '<span class="tag" title="Ráster · Alta eficiencia · Vectorial · RAW · Capas · '
        'Escaneo · Científico · Texturas · Sistema">IMÁGENES · '
        f"{len(images)}</span>"
    )
    return (
        HTML_PAGE.replace("__ACCEPT__", ",".join(extensions + list(COMPOUND_SUFFIXES)))
        .replace("__TAGS__", tags)
        .replace("__EXTENSIONS__", json.dumps(extensions))
        .replace("__COMPOUND__", json.dumps(list(COMPOUND_SUFFIXES)))
        .replace("__IMAGE_EXTENSIONS__", json.dumps(images))
        .replace("__MAX_BYTES__", str(MAX_FILE_SIZE))
        .replace("__MAX_MB__", str(MAX_FILE_SIZE // (1024 * 1024)))
        .replace("__NONCE__", nonce)
        .replace("__APP_NAME__", html.escape(APP_NAME))
        .replace("__ORG__", html.escape(ORGANIZATION))
        .replace("__AUTHORS__", html.escape(AUTHORS))
    )


class LocalServer(ThreadingHTTPServer):
    """Servidor HTTP multihilo local con límite de concurrencia."""
    daemon_threads, allow_reuse_address = True, True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._slots = threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)

    def process_request(self, request: Any, client_address: Any) -> None:
        """Admite la conexión solo si hay un hueco libre."""
        if not self._slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Length: 0\r\nConnection: close\r\n\r\n"
                )
            except OSError:
                pass
            finally:
                self.close_request(request)
            return
        super().process_request(request, client_address)

    def shutdown_request(self, request: Any) -> None:
        """Libera el hueco de concurrencia al cerrar la conexión."""
        try:
            super().shutdown_request(request)
        finally:
            self._slots.release()


class RequestHandler(BaseHTTPRequestHandler):
    """Manejador de rutas y extracción de metadatos."""
    server_version = f"{ORGANIZATION}-MetaDatos/{__version__}"
    timeout = REQUEST_TIMEOUT_SECONDS

    def end_headers(self) -> None:
        """Añade cabeceras de seguridad y control de caché."""
        nonce = getattr(self, "_nonce", None)
        headers = [
            ("X-Content-Type-Options", "nosniff"),
            ("Content-Security-Policy", CSP_PAGE.format(nonce=nonce) if nonce else CSP_DEFAULT),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
            ("Permissions-Policy", "geolocation=(), camera=(), microphone=()"),
            ("Cache-Control", "no-store"),
        ]
        for key, value in headers:
            self.send_header(key, value)
        super().end_headers()

    def _allowed_hosts(self) -> set[str]:
        """Hosts admitidos para el servidor local."""
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            hosts |= {"127.0.0.1", "localhost"}
        return hosts

    def _request_allowed(self) -> bool:
        """Valida Host, Origin y Sec-Fetch-Site de la petición."""
        if self.headers.get("Host", "") not in self._allowed_hosts():
            return False
        site = self.headers.get("Sec-Fetch-Site")
        if site is not None and site not in ("same-origin", "none"):
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {
            f"http://{host}" for host in self._allowed_hosts()
        }

    def send_json(self, status: int, data: dict) -> None:
        """Serializa y despacha una respuesta JSON."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Sirve la página web principal o estado de salud."""
        if not self._request_allowed():
            return self.send_json(403, {"error": "Origen no permitido."})
        self._nonce = None
        path = urlsplit(self.path).path
        if path == "/":
            self._nonce = secrets.token_urlsafe(16)
            body = render_page(self._nonce).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/health":
            self.send_json(200, {"status": "ok"})
        else:
            self.send_json(404, {"error": "Ruta no encontrada."})

    def do_POST(self) -> None:
        """Procesa el archivo subido y extrae sus metadatos."""
        if not self._request_allowed():
            return self.send_json(403, {"error": "Origen no permitido."})
        if urlsplit(self.path).path != "/api/extract":
            return self.send_json(404, {"error": "Ruta no encontrada."})
        try:
            try:
                length = int(self.headers.get("Content-Length", 0))
            except (TypeError, ValueError):
                return self.send_json(400, {"error": "Content-Length no válido."})
            if not (0 < length <= MAX_REQUEST_SIZE):
                return self.send_json(413, {"error": "Archivo supera el límite de 40 MB."})
            ctype = self.headers.get("Content-Type", "")
            if not ctype.lower().startswith("multipart/form-data"):
                return self.send_json(415, {"error": "Se esperaba multipart/form-data."})
            with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as body:
                body.write(f"Content-Type: {ctype}\r\n\r\n".encode("latin-1", "replace"))
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 64 * 1024))
                    if not chunk:
                        return self.send_json(400, {"error": "Cuerpo incompleto."})
                    body.write(chunk)
                    remaining -= len(chunk)
                body.seek(0)
                msg = BytesParser(policy=default).parse(body)
                part = next((p for p in msg.iter_parts() if p.get_filename()), None)
                if not part:
                    return self.send_json(400, {"error": "No se recibió un archivo válido."})
                raw_name = part.get_filename() or ""
                filename = Path(raw_name.replace("\\", "/")).name
                if not filename:
                    return self.send_json(400, {"error": "Nombre de archivo no válido."})
                ext = next(
                    (suffix for suffix in COMPOUND_SUFFIXES if filename.lower().endswith(suffix)),
                    Path(filename).suffix.lower(),
                )
                if not is_supported_name(filename):
                    return self.send_json(415, {"error": f"Formato no compatible: {ext}"})
                data = part.get_payload(decode=True) or b""
            if not data:
                return self.send_json(400, {"error": "El archivo está vacío."})
            if len(data) > MAX_FILE_SIZE:
                return self.send_json(413, {"error": "Archivo supera el límite de 40 MB."})
            with tempfile.NamedTemporaryFile(suffix=ext, dir=_temp_root(), delete=False) as tmp:
                tmp.write(data)
                tmp_path = Path(tmp.name)
            try:
                res = extract_file(tmp_path)
                res["file"] = res["filesystem"]["name"] = filename
                self.send_json(200, res)
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception:
            LOGGER.exception("Error interno al procesar %s", self.path)
            try:
                self.send_json(500, {"error": "Error interno al procesar el archivo."})
            except OSError:
                pass

    def log_message(self, fmt: str, *args: object) -> None:
        """Registra logs del servidor en consola."""
        print(f"{self.address_string()} - {fmt % args}")


def main() -> int:
    """Inicia el servidor local y abre la interfaz en el navegador."""
    parser = argparse.ArgumentParser(description="Extractor web de metadatos.")
    parser.add_argument("--port", type=int, default=8766, help="Puerto local (def: 8766)")
    parser.add_argument("--no-browser", action="store_true", help="No abrir navegador")
    args = parser.parse_args()
    addr = f"http://127.0.0.1:{args.port}"
    try:
        server = LocalServer(("127.0.0.1", args.port), RequestHandler)
    except OSError as err:
        parser.exit(2, f"No se pudo iniciar en {addr}: {err}\n")
    print(f"{APP_NAME} — {ORGANIZATION} · {AUTHORS}")
    print(f"Activo en {addr} (Ctrl+C para salir)")
    if not args.no_browser:
        webbrowser.open(addr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
