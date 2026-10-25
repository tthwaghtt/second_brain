// 현황판 · the files screen: the role board (each file's role, how it changes, who edits it), one file's sheet
// (neighbours, history by session, understood, the instruction basket) beside its text or its diff, the tree as the
// location view, and rename / move / delete (to the board's trash) behind a dialog that names what might break.
import { h, s, t, icon, size, confirmDialog, blocks, codeBlock, openView, docName } from './ui.js';
import { titleRow, get, post, refresh, ctx } from './app.js';

const GIT_WORD = { M: '고침 (커밋 안 됨)', '?': '새 파일 (커밋 안 됨)', R: '옮김 (커밋 안 됨)', D: '지움 (커밋 안 됨)', A: '더함 (커밋 안 됨)', '!': 'git에 담지 않음', '': '커밋됨, 바뀐 것 없음' };
const ui = { open: new Set(load('board.open', ['docs', 'docs/session'])), filter: '', note: null, form: null, refs: {}, files: {}, prof: {},
  raw: load('board.raw', false), fresh: load('board.fresh', false), view: 'role', changedOnly: false, notU: false, machine: false, tab: 'text', en: false };
const basket = new Map(load('board.basket', []));
function saveBasket() { try { localStorage.setItem('board.basket', JSON.stringify([...basket])); } catch { /* memory only */ } }

function load(key, dflt) {
  try { return JSON.parse(localStorage.getItem(key)) || dflt; } catch { return dflt; }
}
function save() {
  try { localStorage.setItem('board.open', JSON.stringify([...ui.open])); } catch { /* private window: keep in memory */ }
}

function index(root) {
  const by = {};
  const walk = (n, parent) => { by[n.path] = { ...n, parent }; (n.children || []).forEach(k => walk(k, n.path)); };
  walk(root, null);
  return by;
}

function writing(st) {
  // paths the status document's "진행 중인 세션" table says a running session writes
  const out = [];
  for (const row of st.status?.running || []) {
    const state = Object.entries(row).find(([k]) => k.includes('상태'))?.[1] || '';
    if (!state.startsWith('진행 중')) continue;
    const files = Object.entries(row).find(([k]) => k.includes('파일'))?.[1] || '';
    for (const m of files.matchAll(/`([^`]+)`/g)) out.push(m[1].replace(/\/$/, ''));
  }
  return out;
}

function warnings(node, st, kind) {
  const w = [];
  if (node.git && node.git !== '!') w.push(kind === 'delete' ? '커밋 안 된 변경이 있습니다. 휴지통으로 보내면 그 변경도 함께 갑니다.' : '커밋 안 된 변경이 있습니다. 옮기면 그 변경도 함께 갑니다.');
  if (node.staged) w.push('스테이징되어 있습니다. 다른 세션이 이 파일을 커밋하려는 중일 수 있습니다.');
  if (Date.now() / 1000 - node.mtime < 600) w.push('10분 안에 바뀌었습니다. 다른 세션이 쓰는 중일 수 있습니다.');
  const hit = writing(st).find(p => node.path === p || node.path.startsWith(`${p}/`) || (!p.includes('/') && node.path.split('/').pop() === p));
  if (hit) w.push(`${docName('status', 'STATUS')}의 진행 중인 세션이 쓰는 곳(${hit})입니다.`);
  if (node.kind === 'dir' && node.changed) w.push(`안에 커밋 안 된 변경이 ${node.changed}개 있습니다.`);
  return w;
}

async function refsOf(path) {
  return ui.refs[path] || (ui.refs[path] = await get(`/api/refs?path=${encodeURIComponent(path)}`));
}

function refsBlock(r) {
  if (!r) return null;
  const n = r.live.length, m = r.records.length;
  return h('div', {},
    h('p', { class: 'muted', style: { marginTop: '12px', fontSize: 'var(--fs-sm)' } },
      n ? [`이 경로를 가리키는 곳 `, t(String(n)), '군데는 문서를 고치지 않으므로 옛 경로를 가리키게 됩니다.'] : '이 경로를 가리키는 문서나 코드는 없습니다.',
      m ? [' 고치지 않는 기록 속 ', t(String(m)), '군데는 그대로 두어도 됩니다.'] : ''),
    n ? h('ul', { class: 'refs' }, r.live.slice(0, 40).map(x => h('li', {}, t(`${x.file}:${x.line}`), ' ', h('span', { class: 'muted', text: x.text })))) : null);
}

function resultNote(res) {
  const ck = res.check?.summary;
  const tail = ck ? [' · 문서 검사 ', t(String(ck.problems), ck.problems ? 'bad' : ''), '건'] : '';
  if (res.op === 'delete') return ['휴지통으로 옮겼습니다: ', t(res.from), tail];
  if (res.op === 'restore') return ['되살렸습니다: ', t(res.to), res.made_folder ? ' (있던 폴더를 다시 만듦)' : '', res.sha_ok === false ? ' · 내용이 지울 때와 다릅니다' : '', tail];
  return [res.op === 'move' ? '옮겼습니다: ' : '이름을 바꿨습니다: ', t(res.from), ' → ', t(res.to), tail];
}

async function act(kind, node, extra, st) {
  ui.note = null;
  let r = null;
  try { r = await refsOf(node.path); } catch { /* the dialog says it could not look */ }
  const target = kind === 'rename' ? `${node.path.split('/').slice(0, -1).concat(extra).join('/')}`
    : kind === 'move' ? `${extra ? `${extra}/` : ''}${node.name}` : null;
  const ok = await confirmDialog({
    title: kind === 'rename' ? '이름을 바꿀까요?' : kind === 'move' ? '옮길까요?' : '휴지통으로 옮길까요?',
    what: target ? `${node.path}  →  ${target}` : node.path,
    lines: kind === 'delete'
      ? [`현황판 휴지통으로 옮깁니다. 아래 '휴지통'에서 되살릴 수 있습니다.${node.kind === 'dir' ? ` 폴더 안의 파일 ${node.files}개도 함께 갑니다.` : ''}`,
        node.git === '' ? 'git이 추적하는 파일이라, 커밋하기 전까지 git에는 "지움"으로 보입니다.' : null].filter(Boolean)
      : ['git mv가 아니라 그냥 옮깁니다(다른 세션의 커밋에 섞이지 않도록). git은 커밋할 때 옮긴 것을 알아봅니다.'],
    warn: warnings(node, st, kind),
    refs: r ? refsBlock(r) : h('p', { class: 'error', text: '가리키는 곳을 찾지 못했습니다.' }),
    confirm: kind === 'rename' ? '이름 바꾸기' : kind === 'move' ? '옮기기' : '휴지통으로 옮기기',
    danger: kind === 'delete',
  });
  if (!ok) return;
  ctx.busy = false;
  const expect = { mtime_ns: node.mtime_ns, size: node.size };
  try {
    const res = kind === 'rename' ? await post('/api/op/rename', { path: node.path, name: extra, expect })
      : kind === 'move' ? await post('/api/op/move', { path: node.path, dest: extra, expect })
        : await post('/api/op/delete', { path: node.path, expect });
    ui.note = { ok: true, body: resultNote(res) };
    ui.form = null;
    ctx.busy = false;
    ui.refs = {};
    const to = res.to || node.parent;
    location.hash = `#/files?p=${encodeURIComponent(to || '')}`;
  } catch (e) {
    ui.note = { ok: false, body: [e.message] };
  }
  await refresh(true);
}

async function restore(item, name) {
  try {
    const res = await post('/api/op/restore', { id: item.id, ...(name ? { name } : {}) });
    ui.note = { ok: true, body: resultNote(res) };
    ui.refs = {};
    location.hash = `#/files?p=${encodeURIComponent(res.to)}`;
  } catch (e) {
    ui.note = { ok: false, body: [e.message], conflict: e.data?.conflict ? item.id : null };
  }
  await refresh(true);
}

function treeRows(by, root, sel, q, changedOnly) {
  const rows = [];
  const show = new Set();
  if (q || changedOnly) {
    for (const n of Object.values(by)) {
      const hit = (q && n.path.toLowerCase().includes(q)) || (changedOnly && n.kind !== 'dir' && n.git && n.git !== '!');
      if (hit && (!changedOnly || !q || n.path.toLowerCase().includes(q))) {
        let p = n.path;
        while (p != null) { show.add(p); p = by[p]?.parent; }
      }
    }
  }
  const walk = (n, depth) => {
    for (const k of n.children || []) {
      if ((q || changedOnly) && !show.has(k.path)) continue;
      const open = k.kind === 'dir' && (ui.open.has(k.path) || ((q || changedOnly) && show.has(k.path)));
      const btn = h('button', {
        class: `node${k.kind === 'dir' ? ' is-dir' : ''}${k.ignored ? ' is-ignored' : ''}`, type: 'button', role: 'treeitem',
        'aria-selected': String(k.path === sel), 'aria-expanded': k.kind === 'dir' ? String(open) : null, 'aria-level': String(depth + 1), tabindex: '-1',
        style: { paddingLeft: `${6 + depth * 14}px` }, 'data-path': k.path,
        title: k.desc ? `${k.path}: ${k.desc}` : k.path,
      },
        k.kind === 'dir' ? icon('chev') : h('span', { 'aria-hidden': 'true' }),
        h('span', { class: 'nm', text: k.name + (k.kind === 'dir' ? '/' : '') }),
        h('span', { class: 'ds', text: k.desc || (k.ignored && k.kind === 'dir' ? 'git에 담지 않음' : '') }),
        h('span', { class: 'flags' },
          k.kind === 'dir' && k.changed ? h('span', { class: 'faint t', style: { fontSize: 'var(--fs-xs)' }, text: String(k.changed) }) : null,
          k.kind !== 'dir' && k.git && k.git !== '!' ? h('span', { class: `gitc ${k.git === '?' ? 'q' : k.git}`, title: GIT_WORD[k.git], text: k.git === '?' ? 'N' : k.git }) : null,
          k.locked ? icon('lock') : null));
      btn.addEventListener('click', () => {
        if (k.kind === 'dir') { if (ui.open.has(k.path)) ui.open.delete(k.path); else ui.open.add(k.path); save(); }
        ui.form = null; ui.note = null;
        location.hash = `#/files?p=${encodeURIComponent(k.path)}&view=tree${changedOnly ? '&changed=1' : ''}`;
      });
      rows.push(btn);
      if (open) walk(k, depth + 1);
    }
  };
  walk(root, 0);
  return rows;
}

// ---------- operations on one path (rename, move, trash), shared by the file sheet and the folder sheet ----------
function opsBlock(node, by, st) {
  const box = h('div', { class: 'ops' });
  const locked = Boolean(node.locked) || node.kind === 'link';
  const rn = h('button', { class: 'btn small', type: 'button', disabled: locked, text: '이름 바꾸기' });
  const mv = h('button', { class: 'btn small', type: 'button', disabled: locked, text: '옮기기' });
  const del = h('button', { class: 'btn small danger', type: 'button', disabled: locked, text: '휴지통으로' });
  box.append(h('div', { class: 'opbar' }, rn, mv, del));
  if (locked) box.append(h('p', { class: 'muted', style: { marginTop: '8px', fontSize: 'var(--fs-sm)' } },
    icon('lock'), ' ', node.kind === 'link' ? '링크는 다루지 않습니다.' : `현황판 자물쇠: ${node.locked}`));
  const formBox = h('div');
  box.append(formBox);
  const showForm = kind => {
    ui.form = kind;
    ctx.busy = true;
    if (kind === 'rename') {
      const input = h('input', { type: 'text', value: node.name, 'aria-label': '새 이름' });
      const go = h('button', { class: 'btn primary small', type: 'button', text: '확인' });
      const run = () => { if (input.value && input.value !== node.name) act('rename', node, input.value, st); };
      go.addEventListener('click', run);
      input.addEventListener('keydown', e => { if (e.key === 'Enter') run(); if (e.key === 'Escape') { ui.form = null; ctx.busy = false; formBox.replaceChildren(); } });
      formBox.replaceChildren(h('div', { class: 'inline-form' }, input, go));
      input.focus();
      input.setSelectionRange(0, node.name.lastIndexOf('.') > 0 && node.kind !== 'dir' ? node.name.lastIndexOf('.') : node.name.length);
    } else if (kind === 'move') {
      const dirs = Object.values(by).filter(n => n.kind === 'dir' && n.path !== node.parent && n.path !== node.path
        && !n.path.startsWith(`${node.path}/`) && !n.ignored && n.dest_ok);
      const sel = h('select', { 'aria-label': '옮길 곳' },
        h('option', { value: '', text: node.parent === '' ? '옮길 폴더를 고르세요' : '(맨 위)' }),
        dirs.filter(n => n.path).map(n => h('option', { value: n.path, text: `${n.path}/` })));
      const go = h('button', { class: 'btn primary small', type: 'button', text: '확인' });
      go.addEventListener('click', () => { if (sel.value || node.parent !== '') act('move', node, sel.value, st); });
      formBox.replaceChildren(h('div', { class: 'inline-form' }, sel, go));
      sel.focus();
    }
  };
  rn.addEventListener('click', () => showForm('rename'));
  mv.addEventListener('click', () => showForm('move'));
  del.addEventListener('click', () => act('delete', node, null, st));
  if (ui.form && !locked) queueMicrotask(() => showForm(ui.form));
  else if (!ui.form) ctx.busy = false;
  return box;
}

function noteLine() {
  if (!ui.note) return null;
  return ui.note.ok
    ? h('p', { class: 'notice', role: 'status' }, h('i', { class: 'lamp', 'aria-hidden': 'true' }), h('span', {}, ui.note.body))
    : h('p', { class: 'error', role: 'alert', style: { marginTop: '0', marginBottom: '12px' } }, ui.note.body);
}

const go = p => { ui.form = null; ui.note = null; location.hash = `#/files?p=${encodeURIComponent(p)}${ui.view === 'tree' ? '&view=tree' : ''}`; };
const check = () => s('svg', { viewBox: '0 0 12 12', class: 'ok-mark', 'aria-hidden': 'true' }, s('path', { d: 'M2.5 6.5l2.2 2.2 4.8-5', fill: 'none' }));
// a date and time, zero-padded as clocks are (taste-skill-ignore: not an index number)
const day = x => { const d = new Date(x * 1000); return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

// ---------- A. the role board: one lane per role, the role's own way of changing, who edits it ----------
const ROLE_ORDER = ['규칙·입구', '규칙', '기준', '흐름', '기록', '코드', '데이터', '보고서', '사용자 자료', '옛 방향', '분류 안 됨'];

function visible(f) {
  const q = ui.filter.trim().toLowerCase();
  if (q && !f.path.toLowerCase().includes(q) && !(f.desc || '').toLowerCase().includes(q)) return false;
  if (ui.changedOnly && !(f.git && f.git !== '!')) return false;
  if (ui.notU && f.understood === 'yes') return false;
  return true;
}

function marks(f) {
  return [
    f.understood === 'yes' ? h('span', { class: 'mk ok', title: '파악함' }, check()) : null,
    f.understood === 'changed' ? h('span', { class: 'pill warn', text: '다시 볼 것' }) : null,
    f.git && f.git !== '!' ? h('span', { class: `gitc ${f.git === '?' ? 'q' : f.git}`, title: GIT_WORD[f.git], text: f.git === '?' ? 'N' : f.git }) : null,
    ui.fresh && f.stale?.length ? h('span', { class: 'mk stale', title: `가리키는 ${f.stale.length}개가 더 최근에 바뀜` }, t(String(f.stale.length))) : null,
    f.writers?.length ? h('span', { class: 'pill', title: `${docName('roadmap', 'ROADMAP')}의 쓸 파일`, text: `${f.writers.join('·')} 씀` }) : null,
    basket.has(f.path) ? h('span', { class: 'pill accent', text: basket.get(f.path) === 'write' ? '고칠 것' : '읽을 것' }) : null,
  ];
}

function lanes(ix, sel, compact) {
  const groups = new Map();
  for (const f of ix.files) {
    if (!visible(f)) continue;
    const key = f.tier === 3 ? '__machine' : f.role;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(f);
  }
  const order = [...groups.keys()].filter(k => k !== '__machine').sort((a, b) => {
    const ta = groups.get(a)[0].tier, tb = groups.get(b)[0].tier;
    const ia = ROLE_ORDER.indexOf(a), ib = ROLE_ORDER.indexOf(b);
    return ta - tb || (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
  });
  const out = [];
  for (const role of order) {
    const list = groups.get(role).sort((a, b) => a.path.localeCompare(b.path));
    const f0 = list[0];
    const inferred = list.some(f => f.inferred);
    const big = f0.tier === 0 && !compact;
    const items = list.map(f => h('button', {
      class: `fcard w${f.tier}${big ? ' big' : ''}`, type: 'button', 'aria-current': f.path === sel ? 'true' : null,
      title: `${f.path}${f.desc ? `: ${f.desc}` : ''}`, onclick: () => go(f.path),
    }, h('span', { class: 'fn' }, f.name, f.locked ? icon('lock') : null, h('span', { class: 'marks' }, marks(f))),
      big ? h('span', { class: 'fd', text: f.desc || 'MAP에 설명 없음' }) : compact ? null : h('span', { class: 'fp', text: f.path.split('/').slice(0, -1).join('/') || '맨 위' })));
    out.push(h('section', { class: `lane${compact ? ' compact' : ''}` },
      h('div', { class: 'lane-h' }, h('h2', { class: 'lane-name', text: role }), inferred && ix.map_roles ? h('span', { class: 'pill', title: `${docName('map', 'MAP')}.md 역할 표에 없어서 규칙으로 짐작함`, text: '추정' }) : null,
        h('span', { class: 't faint', text: String(list.length) }),
        compact ? null : h('span', { class: 'lane-how' }, f0.how, f0.who ? ` · 고치는 쪽: ${f0.who}` : '')),
      h('div', { class: `lane-items${big ? ' big' : ''}` }, items)));
  }
  const machine = groups.get('__machine') || [];
  if (machine.length) {
    const counts = {};
    machine.forEach(f => { counts[f.role] = (counts[f.role] || 0) + 1; });
    const toggle = h('button', { class: 'link quiet', type: 'button', text: ui.machine ? '접기' : '펼쳐 보기' });
    toggle.addEventListener('click', () => { ui.machine = !ui.machine; ctx.rerender(); });
    const body = ui.machine
      ? h('div', { class: 'lane-items' }, machine.sort((a, b) => a.path.localeCompare(b.path)).slice(0, 400).map(f => h('button', {
        class: 'fcard w3', type: 'button', 'aria-current': f.path === sel ? 'true' : null, title: f.path, onclick: () => go(f.path),
      }, h('span', { class: 'fn' }, f.name), compact ? null : h('span', { class: 'fp', text: f.path.split('/').slice(0, -1).join('/') }))))
      : h('p', { class: 'muted', style: { fontSize: 'var(--fs-sm)' } }, Object.entries(counts).map(([k, n], i) => [i ? ' · ' : '', `${k} `, t(String(n))]));
    out.push(h('section', { class: `lane machine${compact ? ' compact' : ''}` },
      h('div', { class: 'lane-h' }, h('h2', { class: 'lane-name', text: '기계가 만든 것' }), h('span', { class: 't faint', text: String(machine.length) }),
        compact ? null : h('span', { class: 'lane-how', text: '도구가 만들거나 설치한 것. 지휘할 때 볼 필요가 없음' }), toggle), body));
  }
  if (!out.length) out.push(h('p', { class: 'empty', text: '조건에 맞는 파일이 없습니다.' }));
  return out;
}

// ---------- what needs a look: progress, files with no description, new files ----------
function rolesPrompt(st, ix) {
  // paths, chapter names and the check command come from board.toml, so the prompt fits the project it runs in
  const list = ix.undescribed;
  const map = st.docs.map || 'docs/MAP.md', name = map.split('/').pop(), rules = st.docs.rules || 'CLAUDE.md';
  const roles = st.headings?.map_roles || '파일의 역할', tree = st.headings?.map_tree || '폴더 지도';
  return [
    `${st.project}의 기획 책임 세션(문서를 맡아 고치는 세션)이다. ${map}를 파일의 역할을 적는 한 곳으로 만들어 줘.`,
    st.docs.map ? '' : `0. 아직 ${map}가 없다. 먼저 만들어 ${rules}에 등록하고(문서 표가 있으면 그 표에, 없으면 한 줄로), 현황판 설정(board.toml)에서 [docs] map에 그 경로를 적고 [[files.locked]]에도 더해 줘(현황판에서 옮기거나 지우지 않게). board.toml은 이 두 곳만 고쳐.`,
    ix.map_roles ? '' : `1. ${name}에 "${roles}" 장을 만들어, | 경로 | 역할 | 바뀌는 법 | 누가 고치나 | 무게 | 표로 적어 줘. 경로는 \`파일\`이나 \`폴더/\`, 무게는 지휘·작업·참고·기계 중 하나. 역할과 누가 고치나는 ${rules}에 적힌 규칙(있으면 문서 표, 세션 역할, 건드리지 않는 것)에 맞춰 적고, 현황판이 지금 짐작한 역할(현황판 파일 화면의 역할 판)은 참고만 해.`,
    list.length ? `${ix.map_roles ? '1' : '2'}. ${name}의 "${tree}" 장 나무(없으면 만들어서)에 아래 ${list.length}개 파일의 한 줄 설명을 더해 줘. 파일을 열어 보고 쓰고, 모르는 것은 추측하지 말고 나에게 물어봐.\n${list.map(p => `   - ${p}`).join('\n')}` : '',
    st.check_cmd ? `고친 뒤 ${st.check_cmd.join(' ')}가 0인지 확인하고, 바꾼 곳을 짧게 보고해 줘.` : '바꾼 곳을 짧게 보고해 줘.',
  ].filter(Boolean).join('\n');
}

function copyButton(label, text) {
  const b = h('button', { class: 'btn small', type: 'button', text: label });
  b.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(text()); b.textContent = '복사됨'; } catch { b.textContent = '복사하지 못함'; }
    setTimeout(() => { b.textContent = label; }, 2000);
  });
  return b;
}

function attention(ix, st) {
  const bar = (w) => {
    const p = ix.progress[w] || { total: 0, yes: 0, changed: 0 };
    return h('div', { class: 'prog' }, h('span', { class: 'pl', text: w }), h('span', { class: 'ptrack', role: 'img', 'aria-label': `${w} ${p.total}개 중 ${p.yes}개 파악` },
      h('span', { class: 'pfill', style: { width: `${p.total ? (100 * p.yes / p.total) : 0}%` } })), h('span', {}, t(`${p.yes}`), h('span', { class: 'faint', text: ` / ${p.total}` })),
      p.changed ? h('span', { class: 'pill warn', text: `다시 볼 것 ${p.changed}` }) : null);
  };
  const und = h('div', { class: 'att' },
    h('p', { class: 'att-h' }, '설명 없는 파일 ', t(String(ix.undescribed.length), ix.undescribed.length ? '' : 'faint')),
    h('p', { class: 'muted', text: ix.undescribed.length ? `${docName('map', 'MAP')}.md에 한 줄 설명이 없는 문서·코드. 채우는 일은 기획 책임 세션에 시킵니다.` : `모든 문서·코드에 ${docName('map', 'MAP')} 설명이 있습니다.` }),
    ix.undescribed.length ? h('p', { class: 'att-list' }, ix.undescribed.slice(0, 8).map((p, i, a) => h('span', { class: 'nw' }, h('button', { class: 'ref', type: 'button', onclick: () => go(p), text: p.split('/').pop() }), i < a.length - 1 ? ', ' : '')), ix.undescribed.length > 8 ? ` 외 ${ix.undescribed.length - 8}개` : '') : null,
    h('div', { class: 'att-act' }, copyButton(ix.map_roles ? '설명 채우기 프롬프트 복사' : '역할 표·설명 프롬프트 복사', () => rolesPrompt(st, ix))));
  const rev = h('div', { class: 'att' },
    h('p', { class: 'att-h' }, '새 파일 검토함 ', t(String(ix.review.length), ix.review.length ? '' : 'faint')),
    h('p', { class: 'muted', text: ix.review.length ? '세션이 새로 만들었고 아직 커밋도 MAP 설명도 없는 파일. 무엇인지 먼저 보세요.' : '커밋 안 된 새 파일이 없습니다.' }),
    ix.review.length ? h('p', { class: 'att-list' }, ix.review.slice(0, 10).map((p, i, a) => h('span', { class: 'nw' }, h('button', { class: 'ref', type: 'button', onclick: () => go(p), text: p }), i < a.length - 1 ? ', ' : ''))) : null);
  return [
    ix.map_roles ? null : h('p', { class: 'banner' }, `${docName('map', 'MAP')}.md에 "${st.headings?.map_roles || '파일의 역할'}" 표가 아직 없어서, 역할은 모두 현황판의 `, h('b', { text: '추정' }), '입니다. 아래 "설명 없는 파일" 칸의 프롬프트로 기획 책임 세션에 표를 만들게 할 수 있습니다.'),
    h('section', { class: 'card attention', 'aria-label': '살펴볼 것' },
      h('div', { class: 'att' }, h('p', { class: 'att-h', text: '파악 진도' }), ix.weights.slice(0, 3).map(bar),
        h('p', { class: 'faint', style: { fontSize: 'var(--fs-xs)', marginTop: '4px' }, text: '파일 한 장에서 "파악함"을 누르면 오릅니다. 이 컴퓨터에만 저장.' })),
      und, rev)];
}

// ---------- the instruction basket: pick files, copy a "read these / change these" prompt ----------
function basketPrompt() {
  const reads = [...basket].filter(([, k]) => k === 'read').map(([p]) => p);
  const writes = [...basket].filter(([, k]) => k === 'write').map(([p]) => p);
  return [
    '이번 일에서 다룰 파일입니다.',
    reads.length ? `읽을 것:\n${reads.map(p => `- ${p}`).join('\n')}` : '',
    writes.length ? `고칠 것:\n${writes.map(p => `- ${p}`).join('\n')}` : '',
    '이 목록 밖의 파일은 고치지 말고, 꼭 필요하면 먼저 물어봐 줘.',
  ].filter(Boolean).join('\n');
}

function basketBar() {
  if (!basket.size) return null;
  const clear = h('button', { class: 'link quiet', type: 'button', text: '비우기' });
  clear.addEventListener('click', () => { basket.clear(); saveBasket(); ctx.rerender(); });
  return h('section', { class: 'basket', 'aria-label': '지시 조각' },
    h('span', { class: 'att-h', text: '지시 조각' }),
    h('span', { class: 'bitems' }, [...basket].map(([p, k]) => h('span', { class: 'bitem' }, h('span', { class: 'pill accent', text: k === 'write' ? '고칠 것' : '읽을 것' }), ' ', p.split('/').pop(),
      h('button', { class: 'x', type: 'button', 'aria-label': `${p} 빼기`, onclick: () => { basket.delete(p); saveBasket(); ctx.rerender(); } }, icon('close'))))),
    copyButton('프롬프트 복사', basketPrompt), clear);
}

// ---------- B. the file sheet: role, how it changes, who edits it, neighbours, history ----------
function sheet(f, prof, node, by, st) {
  const card = h('section', { class: 'card sheet', 'aria-labelledby': 'sheet-h' });
  const note = noteLine();
  if (note) card.append(note);
  card.append(h('h2', { id: 'sheet-h', text: f.name }),
    h('p', { class: 'role-line' }, h('b', { text: f.role }), f.inferred ? h('span', { class: 'pill', title: `${docName('map', 'MAP')}.md 역할 표에 없어서 규칙으로 짐작함`, text: '추정' }) : null,
      h('span', { class: 'muted', text: ` · ${['지휘 문서', '작업물', '참고 자료', '기계가 만든 것'][f.tier]}` })));
  const dl = h('dl', { class: 'facts' });
  const add = (k, ...v) => dl.append(h('dt', { text: k }), h('dd', {}, ...v));
  add('위치', t(f.path.split('/').slice(0, -1).join('/') || '맨 위'));
  add('바뀌는 법', f.how || h('span', { class: 'faint', text: '모름' }));
  add('누가 고치나', f.who || h('span', { class: 'faint', text: '모름' }), f.writers.length ? h('span', { class: 'muted' }, ` · ${docName('roadmap', 'ROADMAP')}: ${f.writers.join(', ')}이 씀`) : null);
  add(`${docName('map', 'MAP')} 설명`, f.desc || h('span', { class: 'pill warn', text: `${docName('map', 'MAP')}에 설명 없음` }));
  add('git', GIT_WORD[f.git] || f.git, f.staged ? h('span', { class: 'pill warn', style: { marginLeft: '6px' }, text: '스테이징됨' }) : null);
  add('마지막 변화', t(day(f.last)), f.sessions.length ? h('span', { class: 'muted' }, ` · 바꾼 세션 ${f.sessions.join(', ')}`) : null);
  if (f.readers.length) add('읽는 세션', f.readers.join(', '));
  card.append(dl);
  if (f.stale?.length) {
    card.append(h('p', { class: 'warn-line' }, `이 문서가 가리키는 ${f.stale.length}개가 이 문서보다 나중에 바뀌었습니다: `,
      f.stale.slice(0, 6).map((p, i, a) => h('span', { class: 'nw' }, h('button', { class: 'ref', type: 'button', onclick: () => go(p), text: p.split('/').pop() }), i < a.length - 1 ? ', ' : '')),
      f.stale.length > 6 ? ` 외 ${f.stale.length - 6}개` : ''));
  }
  // understood and the basket
  const und = h('button', { class: `btn small${f.understood === 'yes' ? ' on' : ''}`, type: 'button', 'aria-pressed': String(f.understood === 'yes') },
    f.understood === 'yes' ? [check(), ' 파악함'] : f.understood === 'changed' ? '바뀐 뒤 다시 파악함' : '파악함으로 표시');
  und.addEventListener('click', async () => {
    try { await post('/api/understood', { path: f.path, on: f.understood !== 'yes' }); } catch (e) { ui.note = { ok: false, body: [e.message] }; }
    ctx.store.cache.files = null;
    ctx.rerender();
  });
  const pick = kind => {
    const b = h('button', { class: `btn small${basket.get(f.path) === kind ? ' on' : ''}`, type: 'button', 'aria-pressed': String(basket.get(f.path) === kind),
      text: kind === 'read' ? '지시 조각: 읽을 것' : '지시 조각: 고칠 것' });
    b.addEventListener('click', () => { if (basket.get(f.path) === kind) basket.delete(f.path); else basket.set(f.path, kind); saveBasket(); ctx.rerender(); });
    return b;
  };
  card.append(h('div', { class: 'opbar' }, und, pick('read'), pick('write')));
  if (f.understood === 'changed') card.append(h('p', { class: 'muted', style: { fontSize: 'var(--fs-sm)', marginTop: '6px' }, text: '파악함으로 표시한 뒤 이 파일이 바뀌었습니다. 오른쪽 "바뀐 내용"을 보고 다시 표시하세요.' }));
  // neighbours: one step only
  const nb = (title, list) => h('div', { class: 'nbs' }, h('p', { class: 'label' }, title, ' ', t(String(list.length))),
    list.length ? h('ul', {}, list.slice(0, 12).map(x => h('li', {}, h('button', { class: 'nb', type: 'button', onclick: () => go(x.path), title: x.desc || x.path },
      h('b', { text: x.path.split('/').pop() }), h('span', { class: 'muted', text: ` ${x.role}` })))), list.length > 12 ? h('li', { class: 'muted', text: `외 ${list.length - 12}` }) : null)
      : h('p', { class: 'faint', style: { fontSize: 'var(--fs-sm)' }, text: '없음' }));
  if (prof) card.append(h('div', { class: 'nb2' }, nb('이 파일을 가리키는 곳', prof.in_files), nb('이 파일이 가리키는 곳', prof.out_files)));
  // history: date and session, the English message only on request
  if (prof?.history.length) {
    const showEn = h('button', { class: 'link quiet', type: 'button', text: ui.en ? '영어 원문 접기' : '영어 원문 보기' });
    showEn.addEventListener('click', () => { ui.en = !ui.en; ctx.rerender(); });
    card.append(h('div', { class: 'hist' }, h('p', { class: 'label' }, '바뀐 기록 (커밋) ', t(String(f.commits)), ' ', showEn),
      h('ul', {}, prof.history.map(c => h('li', {}, t(c.when.slice(5, 16).replace('T', ' ')), ' ',
        c.session ? h('span', { class: 'pill', text: c.session }) : h('span', { class: 'faint', text: '세션 모름' }), ' ', t(c.short, 'faint'),
        ui.en ? h('span', { class: 'muted en', text: ` ${c.subject}` } ) : null)))));
  }
  if (node) card.append(opsBlock(node, by, st));
  return card;
}

function folderSheet(node, by, st) {
  const card = h('section', { class: 'card sheet', 'aria-labelledby': 'sheet-h' });
  const note = noteLine();
  if (note) card.append(note);
  card.append(h('h2', { id: 'sheet-h', text: `${node.name}/` }),
    h('dl', { class: 'facts' },
      h('dt', { text: '위치' }), h('dd', {}, t(node.parent || '맨 위')),
      h('dt', { text: '종류' }), h('dd', { text: `폴더 · 파일 ${node.files}개 · ${size(node.size)}` }),
      h('dt', { text: 'git' }), h('dd', { text: node.ignored ? 'git에 담지 않음' : node.changed ? `안에 커밋 안 된 변경 ${node.changed}개` : '안에 바뀐 것 없음' }),
      node.desc ? [h('dt', { text: 'MAP 설명' }), h('dd', { text: node.desc })] : null),
    opsBlock(node, by, st));
  return card;
}

// ---------- the right pane: the file as written, or what changed ----------
function diffView(rel) {
  const box = h('div', { class: 'viewer-body diff' }, h('p', { class: 'muted', text: '불러오는 중…' }));
  get(`/api/diff?path=${encodeURIComponent(rel)}`).then(d => {
    const head = d.kind === 'new' ? '새 파일: 전체가 더해진 줄입니다' : d.kind === 'uncommitted' ? '커밋 안 된 변경 (지금 HEAD와 비교)'
      : d.kind === 'last_commit' ? `바뀐 것 없음 · 마지막 커밋(${d.commit.when.slice(5, 16).replace('T', ' ')}, ${d.commit.short})에서 바뀐 것` : '바뀐 기록이 없습니다';
    const pre = h('pre', { class: 'code diffcode' }, d.rows.map(r => h('span', { class: `ln ${r.k}`, text: r.t || ' ' })));
    box.replaceChildren(h('p', { class: 'muted', style: { marginBottom: '8px', fontSize: 'var(--fs-sm)' }, text: head }), d.rows.length ? pre : h('p', { class: 'faint', text: '보여 줄 줄이 없습니다.' }));
  }).catch(e => box.replaceChildren(h('p', { class: 'error', text: `바뀐 내용을 읽지 못했습니다: ${e.message}` })));
  return box;
}

function rightPane(node, by) {
  const tab = ui.tab || 'text';
  const tabs = h('div', { class: 'tabs', role: 'tablist', 'aria-label': '원문과 바뀐 내용' }, [['text', '원문'], ['diff', '바뀐 내용']].map(([k, label]) => {
    const b = h('button', { class: 'tab', type: 'button', role: 'tab', id: `tab-${k}`, 'aria-controls': 'pane-body',
      'aria-selected': String(tab === k), tabindex: tab === k ? '0' : '-1', text: label });
    b.addEventListener('click', () => { ui.tab = k; ctx.rerender(); });
    b.addEventListener('keydown', e => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      ui.tab = ui.tab === 'diff' ? 'text' : 'diff';
      ctx.rerender();
      queueMicrotask(() => document.getElementById(`tab-${ui.tab}`)?.focus());
    });
    return b;
  }));
  const body = tab === 'diff' && node.kind === 'file' ? h('section', { class: 'viewer' }, diffView(node.path)) : viewer(node, by);
  return h('section', { class: 'card pane' }, node.kind === 'file' ? tabs : null,
    h('div', { id: 'pane-body', role: node.kind === 'file' ? 'tabpanel' : null, 'aria-labelledby': node.kind === 'file' ? `tab-${tab}` : null },
      body || h('p', { class: 'empty', text: '이 폴더에는 README가 없습니다.' })));
}

// the file itself: markdown drawn as a document (or as written), code with line numbers, a picture, or why not
function viewer(node, by) {
  const box = h('section', { class: 'viewer', 'aria-label': '원문' });
  let target = node;
  if (node.kind === 'dir') {
    const readme = (by[node.path]?.children || []).find(k => /^readme\.md$/i.test(k.name));
    if (!readme) return null;
    target = readme;
  }
  if (target.kind !== 'file') return null;
  const key = `${target.path}@${target.mtime_ns}`;
  const head = h('div', { class: 'viewer-head' },
    h('h3', {}, '원문', target !== node ? h('span', { class: 'muted', style: { fontWeight: '400' }, text: ` · 이 폴더의 ${target.name}` }) : null));
  const body = h('div', { class: 'viewer-body' }, h('p', { class: 'muted', text: '불러오는 중…' }));
  box.append(head, body);
  const paint = data => {
    const tools = h('div', { class: 'viewer-tools' });
    const make = () => data.kind === 'md' && !ui.raw ? blocks(data.text, ctx, 4) : data.kind === 'image'
      ? h('img', { src: data.url, alt: data.path, class: 'viewer-img' }) : data.kind === 'binary'
        ? h('p', { class: 'empty', text: `글자로 볼 수 없는 파일입니다 (${data.ext}, ${size(data.size)}).` }) : codeBlock(data.text);
    if (data.kind === 'md') {
      const tog = h('button', { class: 'link quiet', type: 'button', 'aria-pressed': String(ui.raw), text: ui.raw ? '보기 좋게' : '쓴 그대로' });
      tog.addEventListener('click', () => {
        ui.raw = !ui.raw;
        try { localStorage.setItem('board.raw', JSON.stringify(ui.raw)); } catch { /* keep in memory */ }
        tog.textContent = ui.raw ? '보기 좋게' : '쓴 그대로';
        tog.setAttribute('aria-pressed', String(ui.raw));
        body.replaceChildren(make(), ...(data.truncated ? [h('p', { class: 'muted', text: '512 KB까지만 보여 줍니다.' })] : []));
      });
      tools.append(tog);
    }
    if (data.kind === 'md' || data.kind === 'text') {
      tools.append(h('span', { class: 'faint' }, t(String(data.lines)), '줄'),
        h('button', { class: 'link quiet', type: 'button', text: '크게 보기',
          onclick: () => openView(data.path, '원문 (고치지 않고 보여 주기만 함)', make()) }));
    }
    head.append(tools);
    body.replaceChildren(make(), ...(data.truncated ? [h('p', { class: 'muted', text: '512 KB까지만 보여 줍니다.' })] : []));
  };
  if (ui.files[key]) paint(ui.files[key]);
  else get(`/api/file?path=${encodeURIComponent(target.path)}`)
    .then(data => { ui.files[key] = data; paint(data); })
    .catch(e => body.replaceChildren(h('p', { class: 'error', text: `원문을 열지 못했습니다: ${e.message}` })));
  return box;
}

function refList(r) {
  const part = (title, list) => [h('p', { class: 'label', style: { marginTop: '14px' } }, title, ' ', t(String(list.length))),
    list.length ? h('ul', { class: 'reflist' }, list.map(x => h('li', {}, h('span', { class: 'src', text: `${x.file}:${x.line}` }), h('span', { class: 'txt', text: x.text }))))
      : h('p', { class: 'muted', style: { fontSize: 'var(--fs-sm)' }, text: '없음' })];
  return h('div', {}, part('가리키는 문서와 코드', r.live), r.records.length ? part('고치지 않는 기록 속', r.records) : null,
    r.cut ? h('p', { class: 'faint', text: '너무 많아 200줄에서 멈췄습니다.' }) : null);
}

function trashCard(trash) {
  const card = h('section', { class: 'card', 'aria-labelledby': 'trash-h', style: { marginTop: 'var(--gap)' } },
    h('header', {}, h('h2', { id: 'trash-h', text: '휴지통' }), h('span', { class: 'meta' }, t(String(trash.length)), '개 · tools/board/.trash/')));
  if (!trash.length) { card.append(h('p', { class: 'empty', text: '휴지통이 비어 있습니다. 지운 것은 여기로 와서 되살릴 수 있습니다.' })); return card; }
  const list = h('ul', { class: 'rows' });
  for (const it of trash) {
    const btn = h('button', { class: 'btn small', type: 'button', disabled: !it.present, text: '되살리기' });
    btn.addEventListener('click', () => restore(it));
    const li = h('li', {}, h('span', { class: 'what' }, t(it.path), h('span', { class: 'muted', style: { fontSize: 'var(--fs-xs)' } },
      ` · ${it.kind === 'dir' ? `폴더, 파일 ${it.files}개` : size(it.size)} · `, t(it.deleted_at.slice(5, 16).replace('T', ' ')), it.occupied ? ' · 그 자리에 같은 이름이 있음' : '')), btn);
    list.append(li);
    if (ui.note?.conflict === it.id || it.occupied) {
      const input = h('input', { type: 'text', value: `${it.path.split('/').pop()}`, 'aria-label': '새 이름으로 되살리기' });
      const go = h('button', { class: 'btn small', type: 'button', text: '새 이름으로 되살리기' });
      go.addEventListener('click', () => restore(it, input.value));
      list.append(h('li', {}, h('div', { class: 'inline-form', style: { marginTop: '0', width: '100%' } }, input, go)));
    }
  }
  card.append(list);
  return card;
}

export async function filesView(ctx, r) {
  const store = ctx.store;
  const [ix, tdata] = await Promise.all([
    store.cache.files || get('/api/files').then(x => (store.cache.files = x)),
    store.cache.tree || get('/api/tree').then(x => (store.cache.tree = x)),
  ]);
  const by = index(tdata.root);
  const sel = r.q.get('p');
  ui.view = r.q.get('view') === 'tree' ? 'tree' : 'role';
  ui.changedOnly = r.q.get('changed') === '1';
  const node = sel != null ? by[sel] : null;
  const f = node && node.kind === 'file' ? ix.files.find(x => x.path === sel) : null;
  let prof = null;
  if (f) {
    const key = `${sel}@${store.version}`;
    prof = ui.prof[key] || (ui.prof[key] = await get(`/api/profile?path=${encodeURIComponent(sel)}`).catch(() => null));
  }
  if (node) { let p = node.parent; while (p) { ui.open.add(p); p = by[p]?.parent; } }

  // the list: the role board, or the tree (location)
  const listBox = h('div', { class: `listbox${node ? ' side' : ''}` });
  const treeList = h('div', { class: 'tree', role: 'tree', 'aria-label': '프로젝트 파일' });
  treeList.addEventListener('keydown', e => {          // arrow keys walk the tree
    const nodes = [...treeList.querySelectorAll('.node')];
    const i = nodes.indexOf(document.activeElement);
    if (i < 0) return;
    const cur = nodes[i], dir = cur.getAttribute('aria-expanded');
    if (e.key === 'ArrowDown' && nodes[i + 1]) nodes[i + 1].focus();
    else if (e.key === 'ArrowUp' && nodes[i - 1]) nodes[i - 1].focus();
    else if (e.key === 'ArrowRight' && dir === 'false') cur.click();
    else if (e.key === 'ArrowLeft' && dir === 'true') cur.click();
    else if (e.key === 'ArrowLeft') { const up = by[cur.dataset.path]?.parent; treeList.querySelector(`[data-path="${CSS.escape(up || '')}"]`)?.focus(); }
    else return;
    e.preventDefault();
  });
  const paint = () => {
    if (ui.view === 'tree') {
      treeList.replaceChildren(...treeRows(by, tdata.root, sel, ui.filter.trim().toLowerCase(), ui.changedOnly));
      (treeList.querySelector('[aria-selected="true"]') || treeList.querySelector('.node'))?.setAttribute('tabindex', '0');
      listBox.replaceChildren(h('p', { class: 'tree-key' }, [['N', 'q', '새 파일'], ['M', 'M', '고침'], ['R', 'R', '옮김'], ['D', 'D', '지움']].map(([l, c, w]) =>
        h('span', {}, h('span', { class: `gitc ${c}`, text: l }), w)), h('span', {}, '숫자 = 안의 변경 수'), h('span', {}, icon('lock'), ' 현황판 자물쇠')), treeList);
    } else listBox.replaceChildren(...lanes(ix, sel, Boolean(node)));
  };
  paint();
  queueMicrotask(() => listBox.querySelector('[aria-selected="true"], [aria-current="true"]')?.scrollIntoView({ block: 'nearest' }));

  // the toolbar: the two views, a name filter and three switches
  const seg = h('nav', { class: 'seg', 'aria-label': '보기' }, [['role', '역할 판'], ['tree', '위치 (나무)']].map(([k, label]) =>
    h('a', { class: 'seg-i', 'aria-current': ui.view === k ? 'page' : null, href: `#/files?${sel ? `p=${encodeURIComponent(sel)}&` : ''}${k === 'tree' ? 'view=tree' : ''}`, text: label })));
  const search = h('input', { type: 'text', placeholder: '이름·경로·설명으로 거르기', value: ui.filter, 'aria-label': '파일 거르기' });
  search.addEventListener('input', () => { ui.filter = search.value; paint(); });
  const sw = (label, key, title) => {
    const box = h('input', { type: 'checkbox', checked: Boolean(ui[key]) });
    box.addEventListener('change', () => {
      ui[key] = box.checked;
      if (key === 'fresh') { try { localStorage.setItem('board.fresh', JSON.stringify(ui.fresh)); } catch { /* memory only */ } }
      if (key === 'changedOnly') { location.hash = `#/files?${sel ? `p=${encodeURIComponent(sel)}&` : ''}${ui.view === 'tree' ? 'view=tree&' : ''}${box.checked ? 'changed=1' : ''}`; return; }
      paint();
    });
    return h('label', { class: 'sw', title }, box, label);
  };
  const key = h('p', { class: 'key', 'aria-label': '표시 읽는 법' },
    [['N', '새 파일'], ['M', '고침'], ['R', '옮김'], ['D', '지움']].map(([l, w]) => h('span', {}, h('span', { class: 'gitc', text: l }), w)),
    h('span', {}, check(), '파악함'), h('span', {}, h('span', { class: 'mk stale', text: '2' }), '가리키는 것이 더 최근에 바뀜 (신선도)'),
    h('span', {}, icon('lock'), '현황판 자물쇠 (옮기기·지우기 막음)'), h('span', {}, h('span', { class: 'pill', text: `${store.state.roadmap?.sessions?.[0]?.id || 'S1'} 씀` }), `${docName('roadmap', 'ROADMAP')}의 쓸 파일`));
  const tools = h('div', { class: 'ftools' }, seg, search, sw('바뀐 것만', 'changedOnly', '커밋 안 된 변경이 있는 파일만'),
    sw('파악 안 한 것만', 'notU', '파악함으로 표시하지 않은 파일만'), sw('신선도 겹쳐 보기', 'fresh', '가리키는 파일이 더 최근에 바뀐 문서에 숫자 표시'));

  const counts = [0, 0, 0, 0];
  ix.files.forEach(x => { counts[x.tier] += 1; });
  const sub = h('p', { class: 'finding' }, '파일 ', t(String(ix.files.length)), '개', ...ix.weights.map((w, i) => [h('span', { class: 'sep', text: '·' }), `${w} `, t(String(counts[i]))]),
    h('span', { class: 'sep', text: '·' }), ix.map_roles ? `역할: ${docName('map', 'MAP')}.md` : `역할: 추정 (${docName('map', 'MAP')}.md 표 없음)`);
  if (!node) {
    return [...titleRow('파일', sub), tools, key, ...attention(ix, store.state), basketBar(), noteLine(),
      h('div', { class: ui.view === 'tree' ? 'card tree-card' : 'board-lanes', style: { marginTop: 'var(--gap)' } }, listBox), trashCard(tdata.trash)];
  }
  const middle = f ? sheet(f, prof, node, by, store.state) : folderSheet(node, by, store.state);
  return [...titleRow('파일', sub), tools, key, basketBar(),
    h('div', { class: 'files3', style: { marginTop: 'var(--gap)' } },
      h('aside', { class: 'card side-list', 'aria-label': ui.view === 'tree' ? '파일 나무' : '역할별 파일' },
        h('a', { class: 'link quiet back', href: `#/files${ui.view === 'tree' ? '?view=tree' : ''}` }, s('svg', { viewBox: '0 0 12 12', 'aria-hidden': 'true' }, s('path', { d: 'M7.5 2.5 4 6l3.5 3.5' })), '전체 보기'), listBox),
      middle, rightPane(node, by))];
}
