// 현황판 · shared pieces: DOM building, markdown text rendered with textContent only (never innerHTML),
// the popover, the document drawer and the confirm dialog.

export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'style') for (const [p, x] of Object.entries(v)) { if (p.startsWith('--')) el.style.setProperty(p, x); else el.style[p] = x; }
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

const SVG = 'http://www.w3.org/2000/svg';
export function s(tag, attrs, ...kids) {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, v);
  for (const kid of kids.flat()) if (kid) el.append(kid);
  return el;
}

export const t = (text, cls = '') => h('span', { class: `t ${cls}`.trim(), text });
// a missing value: a short grey bar the screen reader reads as 없음
export const nil = () => h('span', { class: 'nil', role: 'img', 'aria-label': '없음' });

export function icon(name) {
  const paths = {
    close: 'M3 3l10 10M13 3L3 13',
    chev: 'M4.5 2.5 8 6l-3.5 3.5',
    lock: 'M3.5 6.5h7v5h-7zM5 6.5V4.8a2 2 0 0 1 4 0v1.7',
  };
  const box = name === 'close' ? '0 0 16 16' : name === 'lock' ? '0 0 14 14' : '0 0 12 12';
  return s('svg', { viewBox: box, class: name === 'chev' ? 'chev' : name === 'lock' ? 'lock' : null, 'aria-hidden': 'true' }, s('path', { d: paths[name] }));
}

// ---------- dates and sizes ----------
export function hm(date) {
  const d = date instanceof Date ? date : new Date(date);
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}
export function day(iso) { return iso ? iso.slice(5, 10) : ''; }
export function stamp(iso) { return iso ? `${iso.slice(5, 10)} ${iso.slice(11, 16)}` : ''; }
export function size(n) {
  if (n == null) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
export function ago(sec) {
  if (sec < 60) return `${Math.max(0, Math.round(sec))}초 전`;
  if (sec < 3600) return `${Math.round(sec / 60)}분 전`;
  if (sec < 86400) return `${Math.round(sec / 3600)}시간 전`;
  return `${Math.round(sec / 86400)}일 전`;
}

// ---------- inline markdown → nodes ----------
// `X.md` "heading" · `X.md` 2·5장 / 1-5·1-11 · `path/to/file` · `code` · **bold** · ~~struck~~
const INLINE = /(`[^`]+\.md`(?:의)?\s*"[^"]{2,40}")|(`[^`]+\.md`\s*(?:\d+(?:-\d+)*\s*(?:·|,|과|와)\s*)*\d+(?:-\d+)*(?:장)?)|(`[^`]+`)|(\*\*[^*]+?\*\*)|(~~[^~]+?~~)/g;

export function inline(text, ctx = {}) {
  const out = [];
  let last = 0;
  if (!text) return out;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const [all, qref, cref, code, bold, strike] = m;
    if (qref) {
      const name = qref.match(/`([^`]+)`/)[1];
      const key = qref.match(/"([^"]+)"/)[1];
      out.push(h('span', { class: 'doc-name', text: name }), ' ',
        h('button', { class: 'ref', type: 'button', onclick: () => openDoc(name, key), text: `"${key}"` }));
    } else if (cref) {
      const name = cref.match(/`([^`]+)`/)[1];
      const rest = cref.slice(cref.indexOf('`', 1) + 1);
      out.push(h('span', { class: 'doc-name', text: name }));
      let pos = 0;
      for (const cm of rest.matchAll(/\d+(?:-\d+)*/g)) {
        out.push(rest.slice(pos, cm.index));
        const ch = cm[0];
        out.push(h('button', { class: 'ref', type: 'button', onclick: () => openDoc(name, ch), 'aria-label': `${name} ${ch}장 열기`, text: ch }));
        pos = cm.index + ch.length;
      }
      out.push(rest.slice(pos));
    } else if (code) {
      const body = code.slice(1, -1);
      if (/^[\w.\-/]+\.md$/.test(body)) {
        out.push(h('button', { class: 'ref doc-name', type: 'button', onclick: () => openDoc(body), text: body }));
      } else if (/^[\w.\-]+\/[\w.\-/]*$/.test(body) && ctx.onPath) {
        out.push(h('button', { class: 'ref doc-name', type: 'button', onclick: () => ctx.onPath(body.replace(/\/$/, '')), text: body }));
      } else {
        out.push(h('code', { text: body }));
      }
    } else if (bold) {
      out.push(h('strong', {}, inline(bold.slice(2, -2), ctx)));
    } else if (strike) {
      out.push(h('s', {}, inline(strike.slice(2, -2), ctx)));
    }
    last = m.index + all.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

// ---------- block markdown for the document drawer ----------
const md = c => c.replace(/[`*~]/g, '').trim();
export function blocks(text, ctx, base = 3) {
  const root = h('div', { class: 'doc' });
  const lines = text.split('\n');
  let i = 0;
  const para = [];
  const flush = () => { if (para.length) { root.append(h('p', {}, inline(para.join(' '), ctx))); para.length = 0; } };
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith('```')) {
      flush();
      const code = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) code.push(lines[i++]);
      root.append(h('pre', { text: code.join('\n') }));
      i++;
      continue;
    }
    const hd = line.match(/^(#{1,6})\s+(.*)$/);
    if (hd) { flush(); root.append(h(`h${Math.min(6, base + Math.max(0, hd[1].length - 2))}`, {}, inline(hd[2], ctx))); i++; continue; }
    if (/^\s*\|/.test(line)) {
      flush();
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]);
      const cells = rows.map(r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
      const body = cells.filter((c, n) => n !== 1 || !c.every(x => /^:?-+:?$/.test(x)));
      const isNum = c => /^[-+±~≈]?\s*[\d.,]+\s*(%|px|m|s|ms|초|분|개|줄|fps|MB|KB|×\s*[\d.,]+)?$/.test(md(c));
      root.append(h('table', {}, body.map((r, n) => h('tr', {}, r.map(c => h(n ? 'td' : 'th', { class: n && isNum(c) ? 'num' : null }, inline(c, ctx)))))));
      continue;
    }
    if (/^>\s?/.test(line)) {
      flush();
      const q = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, ''));
      root.append(h('blockquote', {}, q.map(x => h('p', {}, inline(x, ctx)))));
      continue;
    }
    if (/^\s*(-|\d+\.)\s+/.test(line)) {
      flush();
      const ordered = /^\s*\d+\./.test(line);
      const list = h(ordered ? 'ol' : 'ul');
      while (i < lines.length && (/^\s*(-|\d+\.)\s+/.test(lines[i]) || (/^\s{2,}\S/.test(lines[i]) && list.lastChild))) {
        const l = lines[i++];
        const item = l.match(/^\s*(?:-|\d+\.)\s+(.*)$/);
        if (item) list.append(h('li', {}, inline(item[1], ctx)));
        else list.lastChild.append(' ', ...inline(l.trim(), ctx));
      }
      root.append(list);
      continue;
    }
    if (!line.trim()) { flush(); i++; continue; }
    para.push(line.trim());
    i++;
  }
  flush();
  return root;
}

// ---------- layers ----------
const layer = () => document.getElementById('layer');
let popState = null;

export function closePop() {
  if (!popState) return;
  const { el, anchor } = popState;
  popState = null;
  el.remove();
  anchor?.setAttribute('aria-expanded', 'false');
  anchor?.focus({ preventScroll: true });
}

export function openPop(anchor, content) {
  const same = popState && popState.anchor === anchor;
  closePop();
  if (same) return;
  const el = h('div', { class: 'pop', role: 'dialog', 'aria-modal': 'false', tabindex: '-1' },
    h('button', { class: 'close', type: 'button', 'aria-label': '닫기', onclick: closePop }, icon('close')), content);
  const head = el.querySelector('h3');
  if (head) { head.id = 'pop-h'; el.setAttribute('aria-labelledby', 'pop-h'); }
  layer().append(el);
  anchor.setAttribute('aria-expanded', 'true');
  const r = anchor.getBoundingClientRect();
  const w = el.offsetWidth, ht = el.offsetHeight;
  let left = Math.min(Math.max(16, r.left + r.width / 2 - w / 2), innerWidth - w - 16);
  let top = r.bottom + 8;
  if (top + ht > innerHeight - 16) top = Math.max(16, r.top - ht - 8);
  el.style.left = `${left}px`;
  el.style.top = `${top}px`;
  popState = { el, anchor };
  el.focus({ preventScroll: true });
}

document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  if (popState) { closePop(); return; }
  if (drawerState) closeDrawer();
});
document.addEventListener('pointerdown', e => {
  if (popState && !popState.el.contains(e.target) && !popState.anchor.contains(e.target)) closePop();
});

let drawerState = null;
export let docContext = {};
export function setDocContext(ctx) { docContext = ctx; }
// a document's name for labels ("STATUS", "ROADMAP" …) and a chapter's name, from board.toml [docs] and [headings];
// the fallback when the project has none
export function docName(key, fallback) {
  const p = docContext.docs?.[key];
  return p ? p.split('/').pop().replace(/\.md$/i, '') : fallback;
}
export function docPath(key, fallback) { return docContext.docs?.[key] || fallback; }
export function headName(key, fallback) { return docContext.store?.state?.headings?.[key] || fallback; }

export function closeDrawer() {
  if (!drawerState) return;
  document.querySelector('.app')?.removeAttribute('inert');
  drawerState.el.remove();
  drawerState.scrim.remove();
  const back = drawerState.from;
  drawerState = null;
  back?.focus?.({ preventScroll: true });
}

export function openView(title, label, body) {
  closePop();
  const from = drawerState ? drawerState.from : document.activeElement;
  closeDrawer();
  const el = h('aside', { class: 'drawer', role: 'dialog', 'aria-modal': 'true', 'aria-label': title, tabindex: '-1' },
    h('header', {}, h('h2', { text: title }), label ? h('span', { class: 'label', text: label }) : null),
    h('button', { class: 'close', type: 'button', 'aria-label': '닫기', onclick: closeDrawer }, icon('close')),
    h('div', { class: 'body' }, body));
  const scrim = h('div', { class: 'scrim', onclick: closeDrawer });
  layer().append(scrim, el);
  document.querySelector('.app')?.setAttribute('inert', '');
  drawerState = { el, scrim, from };
  el.focus({ preventScroll: true });
}

// code and plain text with line numbers (the one place monospace is the text face)
export function codeBlock(text) {
  const pre = h('pre', { class: 'code' });
  text.replace(/\n$/, '').split('\n').forEach(line => pre.append(h('span', { class: 'ln', text: line || ' ' })));
  return pre;
}

export async function openDoc(name, ch) {
  closePop();
  const from = drawerState ? drawerState.from : document.activeElement;
  closeDrawer();
  const title = h('h2', { text: `${name}${ch ? ` · ${/^\d/.test(ch) ? ch + '장' : ch}` : ''}` });
  const body = h('div', { class: 'body' }, h('p', { class: 'muted', text: '불러오는 중…' }));
  const el = h('aside', { class: 'drawer', role: 'dialog', 'aria-modal': 'true', 'aria-label': `${name} 원문`, tabindex: '-1' },
    h('header', {}, title, h('span', { class: 'label', text: '원문 (고치지 않고 보여 주기만 함)' })),
    h('button', { class: 'close', type: 'button', 'aria-label': '닫기', onclick: closeDrawer }, icon('close')), body);
  const scrim = h('div', { class: 'scrim', onclick: closeDrawer });
  el.addEventListener('keydown', e => {          // keep Tab inside the drawer while it is open
    if (e.key !== 'Tab') return;
    const f = [...el.querySelectorAll('button, a[href], input, select, [tabindex]:not([tabindex="-1"])')];
    if (!f.length) return;
    if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f.at(-1).focus(); }
    else if (!e.shiftKey && document.activeElement === f.at(-1)) { e.preventDefault(); f[0].focus(); }
  });
  layer().append(scrim, el);
  document.querySelector('.app')?.setAttribute('inert', '');
  drawerState = { el, scrim, from };
  el.focus({ preventScroll: true });
  try {
    const q = new URLSearchParams({ name, ...(ch ? { ch } : {}) });
    const r = await fetch(`/api/doc?${q}`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || '문서를 열지 못했습니다');
    title.textContent = `${data.doc}${data.level ? ` · ${data.title}` : ''}`;
    body.replaceChildren(h('p', { class: 'label', text: `${data.line}번째 줄부터` }), blocks(data.text, docContext));
  } catch (err) {
    body.replaceChildren(h('p', { class: 'error', text: err.message }));
  }
}

// a dialog that names the object and its consequence; resolves true only on the confirm button
export function confirmDialog({ title, what, lines = [], warn = [], refs = null, confirm, danger = false }) {
  return new Promise(resolve => {
    const ok = h('button', { class: `btn ${danger ? 'danger' : 'primary'}`, type: 'button', text: confirm });
    const cancel = h('button', { class: 'btn', type: 'button', text: '그만두기' });
    const d = h('dialog', { class: 'confirm', 'aria-labelledby': 'confirm-title', 'aria-describedby': 'confirm-desc' },
      h('div', { class: 'in' },
        h('h2', { id: 'confirm-title', text: title }),
        what && h('p', { class: 'what', text: what }),
        h('div', { id: 'confirm-desc' }, lines.map(l => h('p', { class: 'muted mt8' }, l))),
        warn.map(w => h('p', { class: 'warn', text: w })),
        refs,
        h('div', { class: 'btns' }, cancel, ok)));
    layer().append(d);
    const done = v => { d.close(); d.remove(); resolve(v); };
    ok.addEventListener('click', () => done(true));
    cancel.addEventListener('click', () => done(false));
    d.addEventListener('cancel', e => { e.preventDefault(); done(false); });
    d.showModal();
    cancel.focus();
  });
}
