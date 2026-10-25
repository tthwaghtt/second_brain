// 현황판 · the roadmap screen: the line diagram, the stages with their sessions, and one session in full.
import { h, t, inline, openDoc, docName } from './ui.js';
import { lineDiagram, legend, stateLine, STATE_WORD } from './line.js';
import { titleRow, get } from './app.js';

const PILL = { done: '', running: 'accent', next: 'accent', planned: '', outline: '', dropped: 'neg' };

function sessionLinks(se, road) {
  const files = (road.files || []).filter(x => x.session === se.id);
  const next = road.edges.filter(e => e[0] === se.id).map(e => e[1]);
  if (!files.length && !next.length) return null;
  const item = x => x.path && !x.path.endsWith('/') ? h('a', { class: 'link', href: `#/files?p=${encodeURIComponent(x.path)}`, text: x.name }) : h('span', { text: x.name });
  return h('dl', { class: 'fieldlist', style: { marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--rule)' } },
    files.some(x => x.kind === 'write') ? [h('dt', { text: '쓰는 파일' }), h('dd', {}, files.filter(x => x.kind === 'write').map((x, i) => [i ? ', ' : '', item(x)]))] : [h('dt', { text: '쓰는 파일' }), h('dd', {}, h('span', { class: 'pill warn', text: `${docName('roadmap', 'ROADMAP')}에 안 적힘` }))],
    files.some(x => x.kind === 'read') ? [h('dt', { text: '읽는 파일' }), h('dd', {}, files.filter(x => x.kind === 'read').map((x, i) => [i ? ', ' : '', item(x), x.chapters.length ? ` ${x.chapters.join('·')}장` : '']))] : null,
    next.length ? [h('dt', { text: '다음 세션' }), h('dd', {}, next.map((id, i) => [i ? ', ' : '', h('a', { class: 'link', href: `#/roadmap/${id}` }, t(id), ' ', road.sessions.find(x => x.id === id)?.short || '')]))] : null);
}

function detail(se, road, ctx) {
  const stage = road.stages.find(x => x.num === se.stage);
  const dl = h('dl', { class: 'fieldlist' });
  if (se.prereqs.length) {
    dl.append(h('dt', { text: '전제' }), h('dd', {}, se.prereqs.map((p, n) => [n ? ', ' : '',
      h('a', { class: 'link', href: `#/roadmap/${p}` }, t(p), ' ', road.sessions.find(x => x.id === p)?.short || '')])));
  }
  for (const f of se.fields) {
    if (f.key === '전제' && se.prereqs.length) {
      const rest = f.text.replace(/^[A-Z]\d+(\s*(승인|,|과|와)\s*)?[.\s]*/, '').trim();
      if (!rest) continue;
      dl.append(h('dt', { text: '전제 (원문)' }), h('dd', {}, inline(f.text, ctx)));
      continue;
    }
    let body;
    if (f.checks) {
      body = h('ul', { class: 'checks' }, f.checks.map(c => h('li', {},
        h('span', { class: `box${c.done ? ' on' : ''}`, role: 'img', 'aria-label': c.done ? '체크됨' : '체크 안 됨' }),
        h('span', {}, inline(c.text, ctx), c.how ? h('span', { class: 'how' }, ' · 확인: ', inline(c.how, ctx)) : null))));
    } else if (f.items.length) {
      body = h('div', {}, f.text ? h('p', {}, inline(f.text, ctx)) : null,
        h(/^\d/.test(f.items[0]) || f.key === '할 일' ? 'ol' : 'ul', {}, f.items.map(x => h('li', {}, inline(x, ctx)))));
    } else {
      body = inline(f.text, ctx);
    }
    dl.append(h('dt', { text: f.key }), h('dd', {}, body));
  }
  return h('section', { class: 'card detail', 'aria-labelledby': 'detail-h' },
    h('header', {}, h('h2', { id: 'detail-h' }, t(se.id), se.title),
      h('button', { class: 'link quiet', type: 'button', onclick: () => openDoc(ctx.docs.roadmap, se.id), text: `${docName('roadmap', 'ROADMAP')} 원문` })),
    h('p', { class: 'muted', style: { marginTop: '2px' } }, [se.role, stage && `단계 ${stage.num} · ${stage.name}`, stateLine(se, stage)].filter(Boolean).join(' · ')),
    se.detail ? dl : h('div', {},
      h('p', { style: { marginTop: '14px' } }, inline(se.title, ctx)),
      h('p', { class: 'empty', text: `이 세션은 ${docName('roadmap', 'ROADMAP')}에 한 줄로만 있습니다${stage?.note ? ` (${stage.note})` : ''}. 목표·할 일·멈출 곳은 앞 단계가 끝난 뒤에 적힙니다.` })),
    sessionLinks(se, road),
    se.fields.find(f => f.key === '완성 기준')?.checks?.length
      ? h('p', { class: 'muted', style: { marginTop: '14px', fontSize: 'var(--fs-xs)' }, text: `네모는 ${docName('roadmap', 'ROADMAP')}에 적힌 그대로입니다. 세션마다 체크하는 법이 달라, 끝남은 세션 머리의 "완료"로만 봅니다.` }) : null);
}

// C. which session writes (filled square) or reads (open square) which file, from ROADMAP's 쓸 파일 and 읽을 것
function grid(road, ix) {
  const links = road.files || [];
  if (!links.length) return h('p', { class: 'empty', text: `${docName('roadmap', 'ROADMAP')}의 세션에 "쓸 파일"이나 "읽을 것"이 적혀 있지 않습니다.` });
  const role = Object.fromEntries((ix?.files || []).map(f => [f.path, f.role]));
  const rows = new Map();
  for (const x of links) {
    const key = x.path || x.name;
    if (!rows.has(key)) rows.set(key, { key, name: x.name, path: x.path, cells: {} });
    const row = rows.get(key);
    row.cells[x.session] = row.cells[x.session] === 'write' || x.kind === 'write' ? 'write' : 'read';
  }
  const list = [...rows.values()].sort((a, b) => {
    const wa = Object.values(a.cells).filter(v => v === 'write').length, wb = Object.values(b.cells).filter(v => v === 'write').length;
    return wb - wa || a.key.localeCompare(b.key);
  });
  const sessions = road.sessions;
  const table = h('table', { class: 'sgrid' },
    h('thead', {}, h('tr', {}, h('th', { scope: 'col', text: '파일' }), sessions.map(se => h('th', { scope: 'col', class: `sh is-${se.state}` },
      t(se.id), h('span', { class: 'muted', text: se.state === 'done' ? '끝남' : se.state === 'running' ? '진행 중' : se.state === 'next' ? '다음' : se.state === 'outline' ? '자세히 안 씀' : '' }))))),
    h('tbody', {}, list.map(row => {
      const writers = Object.entries(row.cells).filter(([, v]) => v === 'write').map(([k]) => k);
      const where = row.path ? (role[row.path.replace(/\/$/, '')] || (row.path.endsWith('/') ? '폴더' : '')) : row.name.startsWith('../') ? '프로젝트 밖' : '아직 없음';
      return h('tr', {},
        h('th', { scope: 'row', class: 'fn' }, row.path && !row.path.endsWith('/') ? h('a', { class: 'link', href: `#/files?p=${encodeURIComponent(row.path)}`, text: row.name.split('/').filter(Boolean).pop() + (row.name.endsWith('/') ? '/' : '') })
          : h('span', { text: row.name.split('/').filter(Boolean).pop() + (row.name.endsWith('/') ? '/' : '') }), h('span', { class: 'muted', text: ` ${where}` }),
          writers.length > 1 ? h('span', { class: 'pill warn', text: `${writers.join('·')}이 함께 씀` }) : null),
        sessions.map(se => h('td', { class: 'c' }, row.cells[se.id] === 'write' ? h('i', { class: 'sq w', role: 'img', 'aria-label': `${se.id} 씀` })
          : row.cells[se.id] ? h('i', { class: 'sq r', role: 'img', 'aria-label': `${se.id} 읽음` }) : null)));
    }),
    h('tr', { class: 'foot' }, h('th', { scope: 'row', class: 'fn muted', text: '"쓸 파일"이 적혀 있나' }), sessions.map(se => h('td', { class: 'c' },
      links.some(x => x.session === se.id && x.kind === 'write') ? h('span', { class: 'muted', text: '적힘' }) : h('span', { class: 'pill warn', text: '안 적힘' }))))));
  return h('div', { class: 'sgrid-wrap' }, table);
}

export async function roadmapView(st, ctx, r) {
  const ix = ctx.store.cache.files || (ctx.store.cache.files = await get('/api/files').catch(() => null));
  const road = st.roadmap;
  if (!road) return [...titleRow('로드맵', h('p', { class: 'finding', text: `이 프로젝트에는 ${docName('roadmap', 'ROADMAP')}이 없습니다.` }))];
  const counts = {};
  for (const se of road.sessions) counts[se.state] = (counts[se.state] || 0) + 1;
  const pick = road.sessions.find(x => x.id === r.arg)
    || road.sessions.find(x => x.state === 'running') || road.sessions.find(x => x.state === 'next') || road.sessions[0];
  const sub = h('p', { class: 'finding' },
    road.header.edition ? `${docName('roadmap', 'ROADMAP')} 판 ${road.header.edition}${road.header.state ? ` · ${road.header.state}` : ''} · ` : '', '세션 ', t(String(road.sessions.length)), '개 중 ',
    Object.entries(counts).map(([k, n], i) => [i ? ', ' : '', `${STATE_WORD[k]} `, t(String(n))]));
  const list = h('section', { class: 'card', 'aria-label': '단계와 세션' });
  for (const stg of road.stages) {
    const block = h('div', { class: 'stage-block' },
      h('h3', {}, t(String(stg.num)), stg.name, stg.period ? h('span', { class: 'muted', style: { fontWeight: '400' }, text: stg.period }) : null),
      stg.checkpoints?.length ? h('p', { class: 'sub' }, '확인 지점: ', stg.checkpoints.join(', ')) : null,
      stg.note ? h('p', { class: 'sub', text: stg.note }) : null);
    for (const id of stg.sessions) {
      const se = road.sessions.find(x => x.id === id);
      block.append(h('a', { class: 'srow', href: `#/roadmap/${id}`, 'aria-current': se === pick ? 'true' : null },
        t(id), h('span', {}, se.short, se.role ? h('span', { class: 'muted', style: { fontSize: 'var(--fs-xs)' }, text: ` · ${se.role.split(',')[0]}` }) : null),
        h('span', { class: `pill ${PILL[se.state]}`, text: STATE_WORD[se.state] })));
    }
    list.append(block);
  }
  const line = h('section', { class: 'card line-card', 'aria-labelledby': 'rl-h', style: { marginTop: '20px' } },
    h('div', { class: 'line-head' }, h('h2', { id: 'rl-h', text: '노선도' }), legend(true)),
    lineDiagram(road, ctx, { selected: pick.id, onPick: id => { location.hash = `#/roadmap/${id}`; } }));
  return [...titleRow('로드맵', sub), line,
    h('div', { class: 'split', style: { marginTop: 'var(--gap)' } }, list, detail(pick, road, ctx)),
    h('h2', { class: 'sec' }, h('span', { text: '세션 × 파일' }), h('span', { class: 'faint', style: { fontWeight: '400' }, text: `채운 네모 = 씀, 빈 네모 = 읽음 · ${docName('roadmap', 'ROADMAP')}의 쓸 파일과 읽을 것` })),
    h('section', { class: 'card' }, grid(road, ix))];
}
