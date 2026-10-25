// 현황판 · the shell: routing, fetching, the 3-second change check, keyboard shortcuts, and the overview screen.
import { h, t, nil, inline, hm, stamp, openDoc, setDocContext, closePop, docName } from './ui.js';
import { lineDiagram, legend, stateLine } from './line.js';
import { historyView } from './history.js';
import { roadmapView } from './roadmap.js';
import { filesView } from './files.js';
import { searchView } from './search.js';

const TOKEN = document.querySelector('meta[name="board-token"]').content;
const view = document.getElementById('view');
const store = { state: null, version: null, checked: null, changed: null, failed: false, pending: false, cache: {}, ui: { promptOpen: false } };
const ROUTES = { 1: '#/', 2: '#/history', 3: '#/roadmap', 4: '#/files', 5: '#/search', '/': '#/search' };

export async function get(path) {
  const r = await fetch(path, { cache: 'no-store' });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(data.error || `${r.status}`), { status: r.status, data });
  return data;
}

export async function post(path, body) {
  const r = await fetch(path, {
    method: 'POST', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-Board-Token': TOKEN },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(data.error || `${r.status}`), { status: r.status, data });
  return data;
}

function route() {
  const hash = location.hash.replace(/^#\/?/, '');
  const [path, query] = hash.split('?');
  const [name, ...rest] = path.split('/');
  return { name: name || 'overview', arg: rest.join('/') || null, q: new URLSearchParams(query || '') };
}

export const ctx = {
  onPath: p => { location.hash = `#/files?p=${encodeURIComponent(p)}`; },
  docs: {},
  busy: false,               // a screen sets this while the user is in the middle of something (a form)
  refresh: () => refresh(true),
  rerender: () => render(),
  get store() { return store; },
};

// the user is in the middle of something: a redraw would take it away, so it waits
function busy() {
  const a = document.activeElement;
  return Boolean(document.querySelector('.pop, .drawer, dialog[open]')) || ctx.busy || store.ui.promptOpen
    || (a && view.contains(a) && a.matches('input, select, textarea'));
}

// ---------- the freshness stamp: when the project last changed, not a ticking clock ----------
function freshness() {
  const el = h('span', { class: 'fresh', 'aria-live': 'polite' });
  const tick = () => {
    if (!el.isConnected) return;
    const sig = `${store.failed}|${store.pending}|${store.changed ? hm(store.changed).slice(0, 5) : ''}`;
    if (el.dataset.sig === sig) return;
    el.dataset.sig = sig;
    const lamp = h('i', { class: `lamp${store.failed ? ' down' : ''}`, 'aria-hidden': 'true' });
    el.title = '3초마다 바뀐 것이 있는지 확인합니다';
    if (store.failed) el.replaceChildren(lamp, '서버에 연결할 수 없음 · 다시 시도하는 중');
    else if (store.pending) {
      el.replaceChildren(lamp, '새 변경이 있습니다 · ',
        h('button', { class: 'link', type: 'button', onclick: () => { store.pending = false; render(); }, text: '다시 그리기' }));
    } else el.replaceChildren(lamp, '마지막 변화 ', t(store.changed ? hm(store.changed).slice(0, 5) : ''));
  };
  tick();
  el._tick = tick;
  return el;
}

export function titleRow(title, finding) {
  return [h('div', { class: 'title-row' }, h('h1', { text: title }), freshness()), finding];
}

// ---------- overview ----------
function current(road) {
  return road?.sessions.find(x => x.state === 'running') || road?.sessions.find(x => x.state === 'next');
}

function finding(st) {
  const parts = [];
  const cur = current(st.roadmap);
  if (cur) parts.push([cur.state === 'running' ? '' : '다음은 ', h('b', {}, `${cur.id} ${cur.short}`), cur.state === 'running' ? ' 진행 중' : '']);
  const due = {};
  for (const d of st.brief?.decide || []) if (d.when?.endsWith('전까지')) due[d.when] = (due[d.when] || 0) + 1;
  for (const [when, n] of Object.entries(due)) parts.push([`${when} 정할 것 `, h('b', { class: 't' }, String(n)), '개']);
  const probs = st.check?.summary?.problems;
  if (probs) parts.push(['문서 검사 ', h('b', { class: 't bad' }, String(probs)), '건']);
  if (st.changes?.total) parts.push(['커밋 안 된 변경 ', h('b', { class: 't' }, String(st.changes.total)), '개']);
  const p = h('p', { class: 'finding' });
  parts.forEach((x, n) => p.append(...(n ? [h('span', { class: 'sep', 'aria-hidden': 'true', text: '·' })] : []), ...x));
  return p;
}

function leadCard(st) {
  const road = st.roadmap;
  const prompt = st.status?.prompt;
  const cur = current(road);
  const stage = cur && road.stages.find(x => x.num === cur.stage);
  const f = key => cur?.fields.find(x => x.key === key);
  const card = h('section', { class: 'card s8', 'aria-labelledby': 'lead-h' });
  card.append(h('header', {}, h('h2', { id: 'lead-h', text: cur?.state === 'running' ? '지금 하는 세션' : '다음 차례' }),
    h('span', { class: 'meta', text: `${docName('status', 'STATUS')} 기준` })));
  // with no session to show (no roadmap, or none running or next) the status document's lines, the
  // reading path and the start prompt below still come from the documents
  if (!cur) {
    card.append(h('p', { class: 'empty', text: road
      ? `${docName('status', 'STATUS')}와 ${docName('roadmap', 'ROADMAP')}에서 지금 하는 세션이나 다음 세션을 찾지 못했습니다.`
      : `이 프로젝트에는 로드맵이 없어 세션 칸은 비어 있습니다. ${docName('status', 'STATUS')}에 적힌 것은 아래에 있습니다.` }));
  } else {
    card.append(
      h('p', { class: 'lead-id' }, t(cur.id), cur.title),
      h('p', { class: 'lead-meta' }, [cur.role, stage && `단계 ${stage.num} · ${stage.name}`, stateLine(cur, stage)].filter(Boolean).join(' · ')));
    const kv = h('dl', { class: 'kv' });
    for (const key of ['목표', '멈출 곳']) if (f(key)) kv.append(h('dt', { text: key }), h('dd', {}, inline(f(key).text, ctx)));
    card.append(kv);
  }
  const now = st.status?.now || [];
  if (now.length) {
    const first = now[0];
    const head = (st.headings?.now || '').replace(/[^\p{L}\p{N}\s]/gu, '').trim();
    card.append(h('div', { class: 'now-line' },
      h('p', { class: 'clamp1' }, h('span', { class: 'label' }, `${docName('status', 'STATUS')} ${head}`), ' ',
        first.lead ? h('strong', {}, inline(first.lead, ctx)) : null, ' ', inline(first.text, ctx)),
      h('button', { class: 'link quiet', type: 'button', onclick: () => openDoc(ctx.docs.status, st.headings?.now), text: `${now.length}줄 모두` })));
  }
  const rp = st.reading;
  if (rp) {
    const stops = [...rp.common.map(x => ({ ...x, ch: x.session_slot && cur ? cur.id : x.ch })), ...((cur && rp.per[cur.id]) || [])];
    const label = d => `${d.doc.replace(/\.md$/, '')}${d.ch ? ` ${/^[\d·]+$/.test(d.ch) ? `${d.ch}장` : d.ch.replace(/[^\p{L}\p{N}\s·-]/gu, '').trim()}` : ''}`;
    card.append(h('div', { class: 'readpath' },
      h('h3', { class: 'label' }, !cur ? `세션을 시작할 때 읽는 길 (${stops.length}곳)` : cur.state === 'running' ? `이 세션이 읽은 길 (${stops.length}곳)` : `${cur.id}이 읽을 길 (${stops.length}곳)`,
        h('span', { class: 'rp-key' }, h('span', {}, h('i', { class: 'f' }), '모든 세션이 읽음'), h('span', {}, h('i'), '이 세션만'))),
      h('ol', { class: 'rp' }, stops.map((d, i) => h('li', { class: i < rp.common.length ? 'all' : '' },
        h('button', { class: 'rp-stop', type: 'button', title: d.why || '', onclick: () => openDoc(d.path || d.doc, /^[\d·]+$/.test(d.ch || '') ? d.ch.split('·')[0] : d.ch || undefined) },
          h('span', { class: 'rp-n t', text: String(i + 1) }), h('span', { class: 'rp-l', text: label(d) })))))));
  }
  if (prompt?.text) {
    const box = h('div', { class: `prompt${store.ui.promptOpen ? ' open' : ''}`, id: 'prompt-text', hidden: !store.ui.promptOpen }, h('span', { class: 'ptext', text: prompt.text }));
    const copy = h('button', { class: 'btn primary', type: 'button', id: 'copy-prompt', title: '단축키 C', text: '시작 프롬프트 복사' });
    copy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(prompt.text);
        copy.textContent = '복사됨';
      } catch {
        const range = document.createRange();
        range.selectNodeContents(box);
        getSelection().removeAllRanges();
        getSelection().addRange(range);
        copy.textContent = '선택했습니다 · ⌘C로 복사';
      }
      setTimeout(() => { copy.textContent = '시작 프롬프트 복사'; }, 2200);
    });
    const toggle = h('button', { class: 'link quiet', type: 'button', 'aria-controls': 'prompt-text',
      'aria-expanded': String(store.ui.promptOpen), text: store.ui.promptOpen ? '프롬프트 접기' : '프롬프트 보기' });
    toggle.addEventListener('click', () => {
      store.ui.promptOpen = box.classList.toggle('open');
      box.hidden = !store.ui.promptOpen;
      toggle.setAttribute('aria-expanded', String(store.ui.promptOpen));
      toggle.textContent = store.ui.promptOpen ? '프롬프트 접기' : '프롬프트 보기';
      if (!store.ui.promptOpen && store.pending) { store.pending = false; render(); }
    });
    const already = prompt.next && road?.sessions.find(x => x.id === prompt.next)?.state === 'running';
    card.append(box, h('div', { class: 'actions' },
      h('div', { class: 'left' },
        h('span', {}, '작성 ', prompt.written ? t(prompt.written.slice(5)) : nil(), ' · 다음 세션 ', prompt.next ? t(prompt.next) : nil(),
          already ? ` (${prompt.next}은 이미 진행 중)` : ''), toggle),
      copy));
  } else {
    card.append(h('p', { class: 'empty', text: `${docName('status', 'STATUS')}에 시작 프롬프트가 없습니다.` }));
  }
  return card;
}

function decideCard(st) {
  const items = st.brief?.decide || [];
  const briefName = (st.docs.brief || 'BRIEF.md').split('/').pop();
  const others = (st.status?.open || []).filter(x => !x.includes(briefName));
  const card = h('section', { class: 'card s4', 'aria-labelledby': 'decide-h' },
    h('header', {}, h('h2', { id: 'decide-h' }, '정할 것 ', h('span', { class: 't muted', text: String(items.length) })),
      st.docs.brief ? h('button', { class: 'link quiet', type: 'button', onclick: () => openDoc(ctx.docs.brief, st.headings?.decide || '정할 것'), text: `${briefName.replace('.md', '')} 원문` }) : null));
  if (!items.length) card.append(h('p', { class: 'empty', text: st.docs.brief ? '기획서에 정할 것이 없습니다.' : '이 프로젝트에는 기획서(board.toml의 brief)가 없습니다.' }));
  card.append(h('ul', { class: 'rows tight' }, items.map(d => h('li', {}, h('span', { class: 'what', text: d.title }), h('span', { class: 'when' }, d.when || nil())))));
  if (others.length) {
    card.append(h('p', { class: 'label', style: { marginTop: '10px' }, text: `다른 문서의 정할 것 (${docName('status', 'STATUS')})` }),
      h('ul', { class: 'rows tight' }, others.map(x => h('li', {}, h('span', { class: 'what clamp2' }, inline(x, ctx))))));
  }
  const recent = (st.directions?.recent || []).slice(-1);
  if (recent.length) {
    card.append(h('p', { class: 'label', style: { marginTop: '10px' }, text: `마지막 사용자 원문 (${docName('directions', 'USER_DIRECTIONS')})` }),
      h('ul', { class: 'rows tight' }, recent.map(d => h('li', {}, h('button', { class: 'ref', type: 'button', onclick: () => openDoc(ctx.docs.directions, String(d.num)) }, t(`${d.num}.`), ` ${d.title}`),
        h('span', { class: 'when' }, t(d.date.slice(5)))))));
  }
  return card;
}

// one typewriter ledger line under the diagram: what moved, the document check, how the plan changed
function ledger(st) {
  const c = st.changes, ck = st.check, b = st.brief;
  const words = { '?': '새 파일', M: '고침', R: '옮김', D: '지움', A: '더함' };
  const item = (...kids) => h('span', { class: 'led' }, ...kids);
  const rerun = h('button', { class: 'link quiet', type: 'button', text: '다시 검사' });
  rerun.addEventListener('click', async () => {
    rerun.textContent = '검사하는 중…';
    try { await post('/api/check', {}); await refresh(true); } catch (e) { rerun.textContent = `실패: ${e.message}`; }
  });
  const row = h('div', { class: 'ledger', role: 'group', 'aria-label': '움직임과 검사' },
    item(h('a', { class: 'link', href: '#/files?changed=1' }, '커밋 안 된 변경 ', c ? t(String(c.total)) : nil()),
      c && c.total ? h('span', { class: 'muted', text: ` (${Object.entries(c.counts).map(([k, n]) => `${words[k] || k} ${n}`).join(', ')}${c.staged ? `, 스테이징됨 ${c.staged}` : ''})` }) : null),
    item('마지막 커밋 ', st.last_commit ? [t(stamp(st.last_commit.when)), ' ', t(st.last_commit.short, 'muted')] : nil()),
    st.check_cmd ? item('문서 검사 ', ck?.ok ? t(String(ck.summary.problems), ck.summary.problems ? 'bad' : '') : nil(), '건',
      ck?.ok ? h('span', { class: 'muted', title: (st.check_cmd || []).join(' ') }, ` · 문서 ${ck.summary.documents}개, ${hm(ck.ran * 1000).slice(0, 5)}`) : null, ' ', rerun)
      : item('문서 검사 ', h('span', { class: 'muted', text: '없음 (board.toml [check])' })),
    item(h('a', { class: 'link', href: '#/history' }, '계획 변화'), ' ',
      h('span', { class: 'chain' }, (st.old || []).map((d, n) => [n ? h('span', { class: 'arrow', 'aria-hidden': 'true', text: '→' }) : null,
        d.open ? h('strong', { text: d.name }) : h('s', { text: d.name })])),
      b?.edition ? [' · 기획서 판 ', t(String(b.edition)), b.state ? ` ${b.state.split(' ')[0]}` : ''] : null));
  const out = [row];
  if (ck?.ok && ck.summary.problems) {
    out.push(h('ul', { class: 'ledger-list' }, ck.items.slice(0, 6).map(it => h('li', {},
      it.file ? [t(it.file), it.line ? [':', t(String(it.line))] : null, ' · '] : null, it.ko || it.raw)),
      ck.items.length > 6 ? h('li', { class: 'muted', text: `외 ${ck.items.length - 6}건` }) : null));
  } else if (ck && !ck.ok) {
    out.push(h('p', { class: 'error', text: `문서 검사가 끝나지 않았습니다: ${ck.error}` }));
  }
  return out;
}

function overview(st) {
  const road = st.roadmap;
  const lineCard = h('section', { class: 'card line-card s12', 'aria-labelledby': 'line-h' },
    h('div', { class: 'line-head' }, h('h2', { id: 'line-h', text: road?.header.edition ? `노선도 · ${docName('roadmap', 'ROADMAP')} 판 ${road.header.edition}` : '노선도' }), legend()),
    road ? lineDiagram(road, ctx) : h('p', { class: 'empty', text: `이 프로젝트에는 ${docName('roadmap', 'ROADMAP')}이 없습니다.` }));
  return [
    ...titleRow('개요', finding(st)),
    h('div', { class: 'grid stretch', style: { marginTop: '18px' } }, leadCard(st), decideCard(st)),
    h('div', { class: 'grid', style: { marginTop: 'var(--gap)' } }, lineCard),
    ...ledger(st),
  ];
}

// ---------- render loop ----------
// the focused control is found again in the new view by its id, path, label or text, so a redraw never drops focus
function focusKey() {
  const a = document.activeElement;
  if (!a || !view.contains(a) || a === view) return null;
  return { id: a.id || null, path: a.dataset?.path || null, label: a.getAttribute('aria-label'), tag: a.tagName, cls: a.className, text: a.textContent.trim().slice(0, 60) };
}
function refocus(k) {
  if (!k) return;
  const pick = k.id && document.getElementById(k.id)
    || (k.path && view.querySelector(`[data-path="${CSS.escape(k.path)}"]`))
    || [...view.querySelectorAll(k.tag)].find(el => (k.label && el.getAttribute('aria-label') === k.label) || (el.className === k.cls && el.textContent.trim().slice(0, 60) === k.text));
  pick?.focus({ preventScroll: true });
}
let renderToken = 0;
async function render({ top = false } = {}) {
  const r = route();
  const mine = ++renderToken;
  closePop();
  document.querySelectorAll('.rail-item').forEach(a => { if (a.dataset.view === r.name) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  const st = store.state;
  if (!st) {
    view.replaceChildren(...titleRow('현황판', h('p', { class: 'finding' }, h('span', { class: 'skeleton' }))),
      store.failed ? h('p', { class: 'banner', text: '서버에 연결할 수 없습니다. python3 tools/board/server.py 가 켜져 있는지 확인해 주세요.' }) : null);
    return;
  }
  document.title = `${st.project} 현황판`;
  let nodes;
  try {
    if (r.name === 'history') nodes = await historyView(ctx, r);
    else if (r.name === 'roadmap') nodes = await roadmapView(st, ctx, r);
    else if (r.name === 'search') nodes = await searchView(ctx, r);
    else if (r.name === 'files') nodes = await filesView(ctx, r);
    else nodes = overview(st);
  } catch (e) {
    nodes = [...titleRow('현황판'), h('p', { class: 'banner', text: `화면을 그리지 못했습니다: ${e.message}` })];
  }
  if (mine !== renderToken) return;
  const scroll = window.scrollY;
  const key = top ? null : focusKey();
  view.replaceChildren(...[nodes].flat(Infinity).filter(Boolean));
  window.scrollTo(0, top ? 0 : scroll);
  refocus(key);
}

export async function refresh(force = false) {
  try {
    const { v } = await get('/api/version');
    store.failed = false;
    store.checked = new Date();
    if (force || v !== store.version) {
      store.state = await get('/api/state');
      if (store.version && v !== store.version) store.changed = new Date();
      store.changed ||= new Date();
      store.version = v;
      store.cache = {};
      ctx.docs = store.state.docs;
      setDocContext(ctx);
      if (force || !busy()) { store.pending = false; await render(); } else store.pending = true;
    }
  } catch (e) {
    store.failed = true;
    if (!store.state) render();
  }
  document.querySelectorAll('.fresh').forEach(el => el._tick?.());
}

window.addEventListener('hashchange', () => {
  ctx.busy = false;
  render({ top: true }).then(() => (view.querySelector('[data-autofocus]') || view).focus({ preventScroll: true }));
});
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') refresh(); });
document.addEventListener('keydown', e => {
  if (e.metaKey || e.ctrlKey || e.altKey || e.isComposing) return;
  if (e.target.closest?.('input, select, textarea, [contenteditable]') || document.querySelector('dialog[open], .drawer')) return;
  if (ROUTES[e.key]) { e.preventDefault(); location.hash = ROUTES[e.key]; }
  else if ((e.key === 'c' || e.key === 'C' || e.key === 'ㅊ') && document.getElementById('copy-prompt')) { e.preventDefault(); document.getElementById('copy-prompt').click(); }
});
setInterval(() => {
  if (document.visibilityState !== 'visible') return;
  if (store.pending && !busy()) { store.pending = false; render(); }
  refresh();
}, 3000);
refresh(true);
