/* Markdown 阅读器 —— 渲染 / 多标签 / 编辑保存 / 查找 */
'use strict';

const $ = (id) => document.getElementById(id);

const el = {
  tabs: $('tabs'),
  docName: $('doc-name'),
  saveState: $('save-state'),
  saveText: $('save-text'),
  preview: $('preview'),
  editor: $('editor'),
  content: $('content'),
  empty: $('empty'),
  menu: $('menu'),
  toast: $('toast'),
  findbar: $('findbar'),
  findInput: $('find-input'),
  findCount: $('find-count'),
};

const state = {
  docs: [],        // {id, path, name, content, saved, mtime, dirty, mode, scroll}
  active: null,    // id
  hits: [],
  hitIndex: -1,
};

let api = null;    // pywebview.api，ready 之后才有
let bootQueue = []; // ready 之前收到的启动参数

/* ---------------------------------------------------------------- 工具 */
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

let toastTimer = null;
function toast(msg, ms = 1900) {
  el.toast.textContent = msg;
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.toast.hidden = true; }, ms);
}

function doc() { return state.docs.find((d) => d.id === state.active) || null; }

function render(md) {
  if (!window.marked) return esc(md).replace(/\n/g, '<br>');
  marked.setOptions({ gfm: true, breaks: false, headerIds: false, mangle: false });
  return marked.parse(md);
}

/* ---------------------------------------------------------------- 标签 */
function paintTabs() {
  el.tabs.innerHTML = '';
  state.docs.forEach((d) => {
    const t = document.createElement('div');
    t.className = 'tab' + (d.id === state.active ? ' active' : '') + (d.dirty ? ' dirty' : '');
    t.title = d.path || d.name;
    t.innerHTML = `<span class="tab-dot"></span>
      <span class="tab-name">${esc(d.name)}</span>
      <button class="tab-close" title="关闭">×</button>`;
    t.addEventListener('mousedown', (e) => {
      if (e.button === 0 && !e.target.classList.contains('tab-close')) selectDoc(d.id);
    });
    t.querySelector('.tab-close').addEventListener('click', (e) => {
      e.stopPropagation();
      closeDoc(d.id);
    });
    el.tabs.appendChild(t);
  });
}

function paintDocbar() {
  const d = doc();
  if (!d) {
    el.docName.textContent = '未打开文件';
    el.saveState.className = 'save-state saved';
    el.saveText.textContent = '—';
    return;
  }
  el.docName.textContent = d.name;
  el.saveState.className = 'save-state ' + (d.dirty ? 'dirty' : 'saved');
  el.saveText.textContent = d.dirty ? '未保存' : '已保存';
  $('btn-edit').classList.toggle('on', d.mode === 'edit');
}

function paintBody() {
  const d = doc();
  el.empty.hidden = !!d;
  if (!d) {
    el.preview.hidden = true;
    el.editor.hidden = true;
    el.preview.innerHTML = '';
    return;
  }
  if (d.mode === 'edit') {
    el.preview.hidden = true;
    el.editor.hidden = false;
    if (el.editor.value !== d.content) el.editor.value = d.content;
    el.editor.focus();
  } else {
    el.editor.hidden = true;
    el.preview.hidden = false;
    const _t0 = performance.now();
    el.preview.innerHTML = render(d.content);
    const _ms = performance.now() - _t0;
    // 强制一次布局，否则拿到的是"插入 DOM 的耗时"，不是"排完版"
    void el.preview.offsetHeight;
    const _layout = performance.now() - _t0;
    plog('render bytes=' + new TextEncoder().encode(d.content).length
      + ' parse=' + _ms.toFixed(1) + 'ms layout=' + _layout.toFixed(1) + 'ms');
    if (window.__benchOnce) { plog('doc_shown'); window.__benchOnce = false; }
  }
}

function selectDoc(id) {
  if (state.active === id) return;
  const cur = doc();
  if (cur) cur.scroll = el.content.scrollTop;
  state.active = id;
  state.hits = [];
  state.hitIndex = -1;
  paintTabs(); paintDocbar(); paintBody();
  const d = doc();
  el.content.scrollTop = d ? (d.scroll || 0) : 0;
  if (api) api.set_title(d ? d.name : '');
}

function addDoc(payload, activate = true) {
  const existing = state.docs.find((d) => d.path && d.path === payload.path);
  if (existing) {
    // 磁盘上更新了就刷新内容
    if (!existing.dirty && payload.mtime !== existing.mtime) {
      existing.content = payload.content;
      existing.saved = payload.content;
      existing.mtime = payload.mtime;
    }
    if (activate) selectDoc(existing.id);
    return existing;
  }
  const d = {
    id: 'd' + Date.now() + Math.random().toString(36).slice(2, 6),
    path: payload.path || '',
    name: payload.name,
    content: payload.content,
    saved: payload.content,
    mtime: payload.mtime || 0,
    dirty: false,
    mode: 'view',
    scroll: 0,
  };
  state.docs.push(d);
  if (!activate) { paintTabs(); return d; }
  state.active = d.id;
  paintTabs(); paintBody();
  paintDocbar();
  if (api) api.set_title(d.name);
  el.content.scrollTop = 0;
  return d;
}

/* 一次打开多个文件时停在第一个：用户先选的那个才是他想看的 */
function addMany(files) {
  const list = files || [];
  if (!list.length) return;
  let first = null;
  list.forEach((f, i) => {
    const d = addDoc(f, false);
    if (i === 0) first = d;
  });
  if (first) selectDoc(first.id);
}

function closeDoc(id) {
  const idx = state.docs.findIndex((d) => d.id === id);
  if (idx < 0) return;
  const d = state.docs[idx];
  if (d.dirty && !confirm(`「${d.name}」还有未保存的修改，确定关闭？`)) return;
  state.docs.splice(idx, 1);
  if (state.active === id) {
    const next = state.docs[Math.min(idx, state.docs.length - 1)];
    state.active = next ? next.id : null;
    paintBody();
    if (api) api.set_title(next ? next.name : '');
  }
  paintTabs(); paintDocbar();
}

/* ---------------------------------------------------------------- 打开 / 保存 */
async function openFiles() {
  if (!api) return;
  const res = await api.open_dialog();
  if (!res.ok && res.error) toast(res.error, 3200);
  addMany(res.files);
}

async function saveDoc(saveAs = false) {
  const d = doc();
  if (!d) return;
  if (saveAs || !d.path) {
    const res = await api.save_as(d.content, d.name || '未命名.md');
    if (res.cancelled) return;
    if (!res.ok) { toast(res.error || '保存失败', 3000); return; }
    d.path = res.path;
    d.name = res.name;
    d.saved = d.content;
    d.dirty = false;
    paintTabs(); paintDocbar();
    if (api) api.set_title(d.name);
    toast('已另存为 ' + d.name);
    return;
  }
  const res = await api.save(d.path, d.content);
  if (!res.ok) { toast(res.error || '保存失败', 3000); return; }
  d.saved = d.content;
  d.dirty = false;
  d.mtime = res.mtime;
  paintDocbar(); paintTabs();
  toast('已保存');
}

/* ---------------------------------------------------------------- 编辑 */
function setMode(mode) {
  const d = doc();
  if (!d) return;
  if (d.mode === 'edit' && mode !== 'edit') {
    d.content = el.editor.value;
    d.dirty = d.content !== d.saved;
  }
  d.mode = mode;
  state.hits = [];
  paintDocbar(); paintBody();
  if (mode === 'edit') el.editor.focus();
}

function toggleMode() {
  const d = doc();
  if (!d) return;
  setMode(d.mode === 'edit' ? 'view' : 'edit');
}

/* ---------------------------------------------------------------- 查找 */
function clearHits() {
  el.preview.querySelectorAll('mark.hit').forEach((m) => {
    m.replaceWith(document.createTextNode(m.textContent));
  });
  el.preview.normalize();
  state.hits = [];
  state.hitIndex = -1;
}

function highlight(q) {
  clearHits();
  if (!q) { el.findCount.textContent = '0 / 0'; return; }
  const walker = document.createTreeWalker(el.preview, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) {
    const p = walker.currentNode.parentNode;
    if (!p || /^(SCRIPT|STYLE|MARK)$/.test(p.nodeName)) continue;
    if (walker.currentNode.nodeValue.trim()) nodes.push(walker.currentNode);
  }
  const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
  nodes.forEach((n) => {
    const text = n.nodeValue;
    re.lastIndex = 0;
    if (!re.test(text)) return;
    re.lastIndex = 0;
    const frag = document.createDocumentFragment();
    let last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (!m[0].length) { re.lastIndex++; continue; }
      if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      const mk = document.createElement('mark');
      mk.className = 'hit';
      mk.textContent = m[0];
      frag.appendChild(mk);
      state.hits.push(mk);
      last = m.index + m[0].length;
    }
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    n.parentNode.replaceChild(frag, n);
  });
  state.hitIndex = state.hits.length ? 0 : -1;
  updateFindUI(true);
}

function updateFindUI(scroll) {
  el.findCount.textContent = state.hits.length
    ? `${state.hitIndex + 1} / ${state.hits.length}` : '0 / 0';
  state.hits.forEach((h, i) => h.classList.toggle('current', i === state.hitIndex));
  if (scroll && state.hitIndex >= 0) {
    const h = state.hits[state.hitIndex];
    const top = h.getBoundingClientRect().top + el.content.scrollTop
      - el.content.clientHeight / 2;
    el.content.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
  }
}

function stepFind(dir) {
  if (!state.hits.length) return;
  state.hitIndex = (state.hitIndex + dir + state.hits.length) % state.hits.length;
  updateFindUI(true);
}

function openFind() {
  const d = doc();
  if (!d) return;
  if (d.mode === 'edit') setMode('view');
  el.findbar.hidden = false;
  el.findInput.focus();
  el.findInput.select();
  if (el.findInput.value) highlight(el.findInput.value);
}

function closeFind() {
  el.findbar.hidden = true;
  clearHits();
  el.findCount.textContent = '0 / 0';
}

/* ---------------------------------------------------------------- 菜单 / 其它动作 */
function showMenu(anchor) {
  const r = anchor.getBoundingClientRect();
  el.menu.hidden = false;
  el.menu.style.top = (r.bottom + 6) + 'px';
  el.menu.style.left = Math.max(8, r.right - 216) + 'px';
}

async function exportHtml() {
  const d = doc();
  if (!d) return;
  let css = '';
  try { css = await (await fetch('style.css')).text(); } catch (_) { /* 单文件运行时没有外部 css */ }
  const html = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>${esc(d.name)}</title>
<style>${css}
body{overflow:auto}
.content{height:auto;overflow:visible}
.md{padding:40px 60px 80px}
</style></head>
<body><div class="content"><article class="md">${render(d.content)}</article></div></body></html>`;
  const res = await api.save_as(html, d.name.replace(/\.(md|markdown|txt)$/i, '') + '.html');
  if (res.ok) toast('已导出 ' + res.name);
  else if (!res.cancelled) toast(res.error || '导出失败', 3000);
}

async function copyAll() {
  const d = doc();
  if (!d) return;
  try {
    await navigator.clipboard.writeText(d.content);
    toast('已复制全文');
  } catch (_) {
    const ta = document.createElement('textarea');
    ta.value = d.content;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    toast('已复制全文');
  }
}

/* ---------------------------------------------------------------- 事件绑定 */
function bind() {
  $('btn-open-tab').addEventListener('click', openFiles);
  $('btn-open-empty').addEventListener('click', openFiles);
  $('btn-edit').addEventListener('click', toggleMode);
  $('btn-find').addEventListener('click', openFind);
  $('btn-more').addEventListener('click', (e) => {
    e.stopPropagation();
    if (!el.menu.hidden) { el.menu.hidden = true; return; }
    showMenu(e.currentTarget);
  });

  el.menu.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    el.menu.hidden = true;
    const d = doc();
    switch (b.dataset.act) {
      case 'open': openFiles(); break;
      case 'save': if (d) saveDoc(); break;
      case 'saveas': if (d) saveDoc(true); break;
      case 'export': exportHtml(); break;
      case 'copy': copyAll(); break;
      case 'reveal': if (d && d.path) api.reveal(d.path); else toast('这个文档还没保存到磁盘'); break;
      default: break;
    }
  });

  document.addEventListener('click', (e) => {
    if (!el.menu.hidden && !el.menu.contains(e.target)) el.menu.hidden = true;
  });

  el.editor.addEventListener('input', () => {
    const d = doc();
    if (!d) return;
    d.content = el.editor.value;
    const dirty = d.content !== d.saved;
    if (dirty !== d.dirty) { d.dirty = dirty; paintTabs(); }
    paintDocbar();
  });

  // Tab 键在编辑器里插入两个空格，而不是跳到下一个控件
  el.editor.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const s = el.editor.selectionStart, t = el.editor.selectionEnd;
      el.editor.value = el.editor.value.slice(0, s) + '  ' + el.editor.value.slice(t);
      el.editor.selectionStart = el.editor.selectionEnd = s + 2;
      el.editor.dispatchEvent(new Event('input'));
    }
  });

  el.findInput.addEventListener('input', () => highlight(el.findInput.value));
  el.findInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); stepFind(e.shiftKey ? -1 : 1); }
    if (e.key === 'Escape') closeFind();
  });
  $('find-next').addEventListener('click', () => stepFind(1));
  $('find-prev').addEventListener('click', () => stepFind(-1));
  $('find-close').addEventListener('click', closeFind);

  $('btn-ai').addEventListener('click', () => {
    toast('AI 润色需要接入模型，当前版本未启用', 2600);
  });

  // 快捷键
  window.addEventListener('keydown', (e) => {
    const mod = e.ctrlKey || e.metaKey;
    if (!mod) {
      if (e.key === 'Escape' && !el.findbar.hidden) closeFind();
      return;
    }
    const k = e.key.toLowerCase();
    if (k === 'o') { e.preventDefault(); openFiles(); }
    else if (k === 's') { e.preventDefault(); saveDoc(e.shiftKey); }
    else if (k === 'e') { e.preventDefault(); toggleMode(); }
    else if (k === 'f') { e.preventDefault(); openFind(); }
    else if (k === 'w') {
      e.preventDefault();
      const d = doc();
      if (d) closeDoc(d.id);
    }
  });

  // 拖放打开
  let dropHint = null;
  window.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (!dropHint) {
      dropHint = document.createElement('div');
      dropHint.className = 'drop-hint';
      dropHint.textContent = '松手打开这个 Markdown 文件';
      document.body.appendChild(dropHint);
    }
  });
  window.addEventListener('dragleave', (e) => {
    if (e.relatedTarget === null && dropHint) { dropHint.remove(); dropHint = null; }
  });
  window.addEventListener('drop', async (e) => {
    e.preventDefault();
    if (dropHint) { dropHint.remove(); dropHint = null; }
    const files = Array.from(e.dataTransfer.files || []);
    if (!files.length) return;
    // WebView2 里 File 对象有时带 path；带就用真实路径（能直接保存回原文件）
    const paths = files.map((f) => f.path).filter(Boolean);
    if (paths.length === files.length && api) {
      const res = await api.open_paths(paths);
      addMany(res.files);
      if (res.error) toast(res.error, 3000);
      return;
    }
    for (const f of files) {
      const text = await f.text();
      addDoc({ name: f.name, content: text, path: '', mtime: 0 });
    }
    toast('已打开（通过拖放打开的文件，保存时会让你选位置）', 2800);
  });
}

/* ---------------------------------------------------------------- 启动 */
async function pullStartup() {
  // 启动参数由前端主动来取，不依赖 Python 侧 evaluate_js 的时机
  if (!api || typeof api.take_startup !== 'function') return;
  try {
    window.__benchOnce = true;      // 只给"启动后首次上屏"打一次点
    const res = await api.take_startup();
    plog('take_startup -> files=' + ((res && res.files) ? res.files.length : 'null')
      + ' err=' + (res && res.error));
    if (res && res.files && res.files.length) addMany(res.files);
    if (res && res.error) toast(res.error, 3200);
  } catch (err) {
    plog('take_startup THREW: ' + (err && err.message));
  }
}

function plog(msg) {
  try { if (api && api.log) api.log(msg); } catch (_) { /* 忽略 */ }
}

let readyDone = false;

async function onReady() {
  if (readyDone) return;
  readyDone = true;
  api = window.pywebview.api;
  plog('onReady: api keys=' + Object.keys(api || {}).join(','));
  window.addEventListener('error', (e) => plog('JS ERROR: ' + e.message));
  window.addEventListener('unhandledrejection', (e) => plog('JS REJECT: ' + (e.reason && e.reason.message)));
  bind();
  plog('bind ok');
  if (bootQueue.length) { applyStartup(bootQueue); bootQueue = []; }
  await pullStartup();
  const d = doc();
  if (!d) paintDocbar();
}

function applyStartup(paths) {
  if (!paths || !paths.length || !api) return;
  api.open_paths(paths).then((res) => {
    addMany(res.files);
    if (res.error) toast(res.error, 3000);
  });
}

window.__startup = function (paths) {
  if (api) applyStartup(paths);
  else bootQueue = bootQueue.concat(paths || []);
};

window.addEventListener('pywebviewready', onReady);

/* 桥接就绪有三种时序：事件先到、app.js 执行时已经就绪、两者错开。
   只靠事件 + 一次即时判断，实测打包后有偶发不触发（窗口起来了但没内容）。
   加一个短轮询兜底，onReady 本身幂等，多调几次无副作用。 */
(function waitForBridge(attempt) {
  if (readyDone) return;
  if (window.pywebview && window.pywebview.api) { onReady(); return; }
  if (attempt >= 60) return;                       // 6 秒还没等到就放弃
  setTimeout(() => waitForBridge(attempt + 1), 100);
})(0);
