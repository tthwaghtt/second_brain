// 현황판 · how the plan changed: day columns (not a time axis: the work crowds into single days), one row per
// source: the directions in old/README.md, the brief's and the roadmap's editions from git, the sessions that
// appeared, finished or dropped between roadmap commits, the user's own words (USER_DIRECTIONS.md) and the commits
// per day; then the brief's changed decisions, old to new.
import { h, t, nil, inline, openDoc, docName, docPath, headName } from './ui.js';
import { titleRow, get } from './app.js';

const md = iso => iso.slice(5, 10);

function editionsMissing(events, key) {
  const seen = new Set(events.map(e => e[key]?.edition).filter(Boolean));
  const max = Math.max(0, ...seen);
  const gone = [];
  for (let n = 1; n < max; n++) if (!seen.has(n)) gone.push(n);
  return gone;
}

function ranges(ids) {
  // B6 B7 B8 → B6–B8 (only for one letter running in order)
  const out = [];
  for (const id of ids) {
    const m = id.match(/^([A-Z])(\d+)$/), prev = out.at(-1);
    if (m && prev && prev.l === m[1] && prev.to + 1 === +m[2]) prev.to = +m[2];
    else out.push(m ? { l: m[1], from: +m[2], to: +m[2] } : { raw: id });
  }
  return out.map(r => r.raw || (r.from === r.to ? `${r.l}${r.from}` : `${r.l}${r.from}–${r.l}${r.to}`)).join(' ');
}

export async function historyView(ctx, r) {
  const store = ctx.store;
  const data = store.cache.history || (store.cache.history = await get('/api/history'));
  const dayset = new Set();
  data.events.forEach(e => dayset.add(md(e.when)));
  data.directions.forEach(d => dayset.add(d.date.slice(5)));
  data.old.forEach(d => { if (d.start) dayset.add(d.start); if (d.end) dayset.add(d.end); });
  Object.keys(data.commits_per_day).forEach(d => dayset.add(d.slice(5)));
  const days = [...dayset].sort();
  const commits = Object.fromEntries(Object.entries(data.commits_per_day).map(([k, n]) => [k.slice(5), n]));
  const col = d => days.indexOf(d) + 2;

  const grid = h('div', { class: 'days', style: { '--days': String(days.length) }, role: 'group', 'aria-label': '날짜별 계획 변화 (날짜 칸)' });
  const perDay = {};          // the same entries, one day after another, for a narrow window
  const row = (name, cells, note) => {
    grid.append(h('div', { class: 'rowname' }, name, note ? h('p', { class: 'faint', style: { fontWeight: '400', fontSize: 'var(--fs-xs)' }, text: note }) : null));
    days.forEach(d => {
      const c = cells[d] || [];
      grid.append(h('div', { class: 'cell' }, c));
      if (c.length) (perDay[d] ||= []).push([name, c.map(n => n.cloneNode(true))]);
    });
  };
  grid.append(h('div', { class: 'rowname dayhead' }));
  days.forEach(d => grid.append(h('div', { class: 'dayhead' }, d, h('small', { text: `커밋 ${commits[d] ?? 0}` }))));

  // directions: one band spanning its days
  const dirRow = h('div', { class: 'rowname', text: '방향' });
  grid.append(dirRow);
  const bands = h('div', { class: 'cell', style: { gridColumn: `2 / span ${days.length}`, display: 'grid', gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))`, gap: '6px' } });
  for (const d of data.old) {
    const a = days.indexOf(d.start), b = d.open ? days.length - 1 : Math.max(a, days.indexOf(d.end ?? d.start));
    bands.append(h('div', { class: `dirtrack ${d.open ? 'current' : 'ended'}`, style: { gridColumn: `${a + 1} / ${b + 2}` },
      title: d.text },
      h('span', { class: 'dt-name', text: d.name }), h('span', { class: 'dt-sub', text: `${d.period} · ${d.open ? '지금 가는 길' : '끊긴 길'} · 남은 것: ${d.left.replace(/`/g, '')}` }),
      d.open ? null : h('span', { class: 'stop', 'aria-hidden': 'true' })));
  }
  if (!data.old.length) bands.append(h('p', { class: 'muted', text: docPath('old_index') ? `${docPath('old_index')}에 방향 표가 없습니다.` : '이 프로젝트에는 옛 방향 표(board.toml의 old_index)가 없습니다.' }));
  grid.append(bands);

  // editions of the brief and the roadmap, from git
  for (const [key, name] of [['brief', '기획서 판'], ['roadmap', '로드맵 판']]) {
    const cells = {};
    let prev = null;
    for (const e of data.events) {
      const ed = e[key];
      if (!ed) continue;
      const sig = `${ed.edition}|${ed.state}`;
      if (sig === prev) continue;
      prev = sig;
      const st = ed.state ? (ed.state.startsWith('승인') ? '승인' : ed.state.startsWith('초안') ? '초안' : ed.state.slice(0, 12)) : '';
      (cells[md(e.when)] ||= []).push(h('span', { class: 'mark' }, '판 ', t(String(ed.edition ?? '?')), st ? h('span', { class: 'pill', text: st }) : null,
        h('span', { class: 'faint t', style: { fontSize: 'var(--fs-xs)' }, text: e.when.slice(11, 16) })));
    }
    const gone = editionsMissing(data.events, key);
    row(name, cells, gone.length ? `판 ${gone.join('·')}: 커밋된 적 없음` : null);
  }

  // sessions that appeared, finished or dropped between roadmap commits
  const sess = {};
  for (const e of data.events) {
    const s = e.sessions;
    if (!s) continue;
    const c = (sess[md(e.when)] ||= []);
    if (s.added.length) c.push(h('span', { class: 'mark' }, h('span', { class: 'pill', text: '생김' }), h('span', { class: 'ids', text: ranges(s.added.map(x => x.id)) })));
    if (s.done.length) c.push(h('span', { class: 'mark' }, h('span', { class: 'pill', text: '끝남' }), h('span', { class: 'ids', text: ranges(s.done.map(x => x.id)) })));
    const cut = s.dropped.filter(x => x.state !== 'done'), filed = s.dropped.filter(x => x.state === 'done');
    if (cut.length) c.push(h('span', { class: 'mark' }, h('span', { class: 'pill neg', text: '중단' }), h('span', { class: 'ids', text: cut.map(x => `${x.id} ${x.short}`).join(', ') })));
    if (filed.length) c.push(h('span', { class: 'mark' }, h('span', { class: 'pill', text: '끝난 채 빠짐' }), h('span', { class: 'ids', text: ranges(filed.map(x => x.id)) })));
  }
  row('세션', sess, '로드맵 커밋 사이');

  // the user's own words
  const words = {};
  for (const d of data.directions) {
    (words[d.date.slice(5)] ||= []).push(h('button', { class: 'link quiet', type: 'button', style: { textAlign: 'left', fontWeight: '400' },
      'data-doc': ctx.docs.directions, 'data-ch': String(d.num) }, t(`${d.num}.`), ' ', d.title));
  }
  row('사용자 원문', words, '원문 기록의 날짜 장');

  const changes = h('ol', { class: 'decisions' });
  for (const c of data.changes) {
    const steps = c.steps;
    const last = steps.at(-1);
    changes.append(h('li', {},
      h('p', { class: 'chain' }, steps.map((st, n) => [n ? h('span', { class: 'arrow', 'aria-hidden': 'true', text: '→' }) : null,
        st.struck ? h('span', {}, inline(st.text, ctx)) : h('strong', {}, inline(st.text, ctx))])),
      h('span', { class: 'when' }, last?.date || nil())));
  }
  const b = data.brief;
  const sub = h('p', { class: 'finding' }, '방향 ', t(String(data.old.length)), '개 · 기획서 판 ',
    b?.edition ? t(String(b.edition)) : nil(), ` ${b?.state || ''} · 사용자 원문 `, t(String(data.directions.length)), '장 · 바뀐 결정 ', t(String(data.changes.length)), '줄');
  return [...titleRow('계획 변화', sub),
    h('h2', { class: 'sec' }, h('span', { text: '날짜별' }), h('span', { class: 'faint', style: { fontWeight: '400' }, text: '결정한 날(원문)과 커밋한 날은 다를 수 있습니다' })),
    h('section', { class: 'card', onclick: e => { const b = e.target.closest('[data-doc]'); if (b) openDoc(b.dataset.doc, b.dataset.ch); } },
      h('div', { class: 'days-wrap' }, grid),
      h('div', { class: 'days-list' }, days.map(d => h('section', { class: 'dl-day' }, h('h3', {}, d, h('small', { class: 'muted', style: { fontFamily: 'var(--font)', fontWeight: '400', marginLeft: '8px' }, text: `커밋 ${commits[d] ?? 0}` })),
        h('dl', {}, data.old.filter(o => o.start && o.start <= d && (o.open || (o.end || o.start) >= d)).length
          ? [h('dt', { text: '방향' }), h('dd', {}, data.old.filter(o => o.start && o.start <= d && (o.open || (o.end || o.start) >= d)).map(o => h(o.open ? 'strong' : 's', { text: o.name })))] : null,
          (perDay[d] || []).map(([n, nodes]) => [h('dt', { text: n }), h('dd', {}, nodes)])))))),
    h('h2', { class: 'sec' }, h('span', { text: `${headName('changes', '바뀐 결정')} · ${docName('brief', 'BRIEF')}` }),
      ctx.docs.brief ? h('button', { class: 'link quiet', type: 'button', onclick: () => openDoc(ctx.docs.brief, headName('changes', '바뀐 결정')), text: '원문' }) : null),
    h('section', { class: 'card' }, data.changes.length ? changes : h('p', { class: 'empty', text: ctx.docs.brief ? '기획서에 바뀐 결정 기록이 없습니다.' : '이 프로젝트에는 기획서(board.toml의 brief)가 없습니다.' }))];
}
