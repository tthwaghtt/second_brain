// 현황판 · the line diagram: sessions are stations, ROADMAP's "전제" are the tracks. Sessions that can run side by
// side sit on their own lanes (the tracks split and merge where the documents say); a session with no stated
// prerequisite joins the end of the stage before it on a dashed track, so no branch is drawn that the documents
// do not state.
import { h, s, t, inline, openDoc, openPop, docName } from './ui.js';

export const STATE_WORD = {
  done: '끝남', running: '진행 중', next: '다음 차례', planned: '남음', outline: '아직 자세히 안 씀', dropped: '빠짐',
};

export function stateLine(se, stage) {
  if (se.state === 'done') return `끝남${se.date ? ` ${se.date}` : ''}`;
  if (se.state === 'running') return se.running?.startsWith('진행 중') ? `${docName('status', 'STATUS')}: ${se.running}` : `진행 중${se.running ? ` · ${docName('status', 'STATUS')}: ${se.running}` : ''}`;
  if (se.state === 'next') return `다음 차례 · ${docName('status', 'STATUS')} 기준`;
  if (se.state === 'outline') return `아직 자세히 안 씀${stage?.note ? ` · ${stage.note}` : ''}`;
  return '남음';
}

const field = (se, key) => se.fields.find(f => f.key === key);

export function sessionCard(se, road, ctx) {
  const stage = road.stages.find(x => x.num === se.stage);
  const kv = h('dl', { class: 'kv' });
  const add = (label, body) => { if (body) kv.append(h('dt', { text: label }), h('dd', {}, body)); };
  if (se.prereqs.length) add('전제', se.prereqs.map((p, n) => [n ? ', ' : '', t(p)]));
  for (const key of ['결과', '목표']) {
    const f = field(se, key);
    if (f) add(key, inline(f.text, ctx));
  }
  const todo = field(se, '할 일');
  if (todo) {
    const items = todo.items.length ? todo.items : [todo.text];
    add('할 일', h('ol', { class: 'todo' }, items.slice(0, 3).map(x => h('li', {}, inline(x, ctx))),
      items.length > 3 ? h('li', { class: 'muted', text: `외 ${items.length - 3}개는 로드맵에서` }) : null));
  }
  const stop = field(se, '멈출 곳');
  if (stop) add('멈출 곳', inline(stop.text, ctx));
  const done = field(se, '완성 기준');
  if (done?.checks?.length) add('완성 기준', `${done.checks.length}가지 중 체크 ${done.checks.filter(c => c.done).length} · 쓸 파일과 읽을 것은 로드맵에서`);
  return h('div', {},
    h('h3', {}, t(se.id), se.title),
    h('p', { class: 'muted', style: { marginTop: '2px', fontSize: 'var(--fs-sm)' } },
      [se.role, stage ? `단계 ${stage.num} · ${stage.name}` : null, stateLine(se, stage)].filter(Boolean).join(' · ')),
    se.detail ? kv : h('p', { class: 'muted', style: { marginTop: '10px' }, text: `${docName('roadmap', 'ROADMAP')}에 한 줄로만 있습니다${stage?.note ? ` (${stage.note})` : ''}. 목표·할 일·멈출 곳은 앞 단계가 끝난 뒤에 적힙니다.` }),
    h('div', { class: 'foot' },
      h('a', { class: 'link', href: `#/roadmap/${se.id}`, text: '로드맵에서 자세히' }),
      h('button', { class: 'link quiet', type: 'button', onclick: () => openDoc(ctx.docs.roadmap, se.id), text: `${docName('roadmap', 'ROADMAP')} 원문` })));
}

function layout(road) {
  const by = Object.fromEntries(road.sessions.map((x, i) => [x.id, { ...x, idx: i, parents: [] }]));
  for (const [a, b] of road.edges) if (by[a] && by[b]) by[b].parents.push(a);
  const depth = {};
  const dep = id => depth[id] ?? (depth[id] = by[id].parents.length ? Math.max(...by[id].parents.map(dep)) + 1 : 0);
  Object.keys(by).forEach(dep);
  const order = Object.values(by).sort((a, b) => depth[a.id] - depth[b.id] || a.idx - b.idx);
  const lane = {}, taken = new Set();
  for (const n of order) {
    let l = n.parents.length ? lane[n.parents[0]] : 0;
    while (taken.has(`${l}:${depth[n.id]}`)) l++;
    lane[n.id] = l;
    taken.add(`${l}:${depth[n.id]}`);
  }
  return { by, depth, lane, maxDepth: Math.max(0, ...Object.values(depth)), lanes: 1 + Math.max(0, ...Object.values(lane)) };
}

// opts.selected marks one station; opts.onPick makes a click select it (the roadmap screen) instead of opening its card
export function lineDiagram(road, ctx, opts = {}) {
  const inner = h('div', { class: 'line-inner' });
  const box = h('div', { class: 'line' }, inner);
  const L = layout(road);
  const list = () => {
    const ol = h('ol', { class: 'line-list' });
    for (const st of road.stages) {
      ol.append(h('li', { class: 'll-stage', text: `단계 ${st.num} · ${st.name}${st.period ? ` · ${st.period}` : ''}` }));
      for (const id of st.sessions) {
        const se = road.sessions.find(x => x.id === id);
        const btn = h('button', { class: `ll-item is-${se.state}${opts.selected === id ? ' is-selected' : ''}`, type: 'button', 'aria-haspopup': opts.onPick ? null : 'dialog' },
          h('span', { class: 'sid', text: se.id }), h('span', { class: 'sname', text: se.short }),
          h('span', { class: 'muted', text: [se.role?.split(',')[0], STATE_WORD[se.state], se.prereqs.length ? `전제 ${se.prereqs.join('·')}` : null].filter(Boolean).join(' · ') }));
        btn.addEventListener('click', () => (opts.onPick ? opts.onPick(se.id) : openPop(btn, sessionCard(se, road, ctx))));
        ol.append(h('li', {}, btn));
      }
    }
    inner.replaceChildren(ol);
    inner.style.width = '';
    inner.style.height = '';
  };
  const draw = () => {
    if (!box.clientWidth) return;
    if (box.clientWidth < 600) { list(); return; }
    const W = Math.max(box.clientWidth, (L.maxDepth + 1) * 136 + 40);   // a station label needs about 128px
    // two lanes: lane 0 is labelled above its track and lane 1 below, so the band between them only holds the kinks
    const padX = 80, labelH = 62, laneH = L.lanes === 2 ? 46 : 96, top = 26;
    const above = L.lanes > 1;
    const y0 = top + (above ? labelH + 14 : 10);
    const yOf = id => y0 + L.lane[id] * laneH;
    const xOf = id => padX + (L.maxDepth ? L.depth[id] * (W - padX * 2) / L.maxDepth : 0);
    const height = y0 + (L.lanes - 1) * laneH + labelH + 18;
    const svg = s('svg', { class: 'tracks', viewBox: `0 0 ${W} ${height}`, height, role: 'img',
      'aria-label': `노선도: 세션 ${road.sessions.length}개, 갈래 ${L.lanes}줄` });
    // stage rules between stages
    const stageX = road.stages.map(st => st.sessions.length ? Math.min(...st.sessions.map(xOf)) : null);
    const bound = road.stages.map(() => 0);       // each stage's left edge: the rule between it and the stage before
    road.stages.forEach((st, n) => {
      if (n && stageX[n] != null && stageX[n - 1] != null) {
        const prevMax = Math.max(...road.stages[n - 1].sessions.map(xOf));
        bound[n] = (prevMax + stageX[n]) / 2;
        svg.append(s('line', { class: 'stage-rule', x1: bound[n], x2: bound[n], y1: 4, y2: height - 4 }));
      }
    });
    for (const [a, b, kind] of road.edges) {
      if (!L.by[a] || !L.by[b]) continue;
      const x1 = xOf(a), y1 = yOf(a), x2 = xOf(b), y2 = yOf(b);
      const dy = Math.abs(y2 - y1), run = Math.min(dy * 0.7, (x2 - x1) / 2);
      let d = `M${x1} ${y1}`;
      if (y1 === y2) d += ` H${x2}`;
      else if (y2 > y1) d += ` H${x1 + 16} L${x1 + 16 + run} ${y2} H${x2}`;
      else d += ` H${x2 - 16 - run} L${x2 - 16} ${y2} H${x2}`;
      const ran = L.by[a].state === 'done' && ['done', 'running', 'next'].includes(L.by[b].state);
      svg.append(s('path', { class: `track${ran ? ' ran' : ''}${kind === 'order' ? ' order' : ''}`, d }));
    }
    const kids = [svg];
    road.stages.forEach((st, n) => {
      if (stageX[n] == null) return;
      const left = n ? bound[n] + 10 : 0, right = n + 1 < road.stages.length && bound[n + 1] ? bound[n + 1] - 10 : W;
      kids.push(h('div', { class: 'stage-name', title: `단계 ${st.num} ${st.name}${st.period ? ` · ${st.period}` : ''}`, style: { left: `${left}px`, maxWidth: `${right - left}px` } },
        `단계 ${st.num} · `, h('b', { text: st.name }), st.period ? ` · ${st.period}` : ''));
    });
    for (const se of road.sessions) {
      const x = xOf(se.id), y = yOf(se.id);
      const g = s('g', { 'data-id': se.id, class: 'st' });
      if (se.state === 'done') g.append(s('circle', { class: 'st-done', cx: x, cy: y, r: 7 }));
      else if (se.state === 'running') g.append(s('circle', { class: 'st-ring', cx: x, cy: y, r: 12 }), s('circle', { class: 'st-dot', cx: x, cy: y, r: 7 }));
      else if (se.state === 'next') g.append(s('circle', { class: 'st-next', cx: x, cy: y, r: 9 }), s('circle', { class: 'st-dot', cx: x, cy: y, r: 3.5 }));
      else if (se.state === 'outline') g.append(s('circle', { class: 'st-outline', cx: x, cy: y, r: 6 }));
      else g.append(s('circle', { class: 'st-planned', cx: x, cy: y, r: 7 }));
      svg.append(g);
      const up = above && L.lane[se.id] === 0;
      const tag = se.state === 'running' ? '진행 중' : se.state === 'next' ? '다음' : null;
      const picked = opts.selected === se.id;
      const btn = h('button', {
        class: `station is-${se.state}${picked ? ' is-selected' : ''}`, type: 'button',
        'aria-haspopup': opts.onPick ? null : 'dialog', 'aria-expanded': opts.onPick ? null : 'false', 'aria-current': picked ? 'true' : null,
        'aria-label': `${se.id} ${se.title}, ${STATE_WORD[se.state]}. ${opts.onPick ? '눌러서 고르기' : '눌러서 할 일 보기'}`,
        style: { left: `${x}px`, top: up ? `${y - 14}px` : `${y + 14}px`, transform: up ? 'translate(-50%, -100%)' : 'translateX(-50%)' },
      },
        up && tag ? h('span', { class: 'stag', text: tag }) : null,
        h('span', { class: 'sid', text: se.id }),
        h('span', { class: 'sname', text: se.short }),
        se.role ? h('span', { class: 'srole', text: se.role.split(',')[0] }) : null,
        !up && tag ? h('span', { class: 'stag', text: tag }) : null);
      const open = () => (opts.onPick ? opts.onPick(se.id) : openPop(btn, sessionCard(se, road, ctx)));
      btn.addEventListener('click', open);
      g.addEventListener('click', open);
      kids.push(btn);
    }
    inner.replaceChildren(...kids);
    inner.style.width = `${W}px`;
    inner.style.height = `${height + 12}px`;     // room for the lowest label's focus ring
  };
  // draw once the box is in the page, and again whenever its width changes
  let width = 0;
  new ResizeObserver(() => { if (box.clientWidth !== width) { width = box.clientWidth; draw(); } }).observe(box);
  const first = () => { if (!width && box.clientWidth) { width = box.clientWidth; draw(); } };
  requestAnimationFrame(first);
  setTimeout(first, 60);     // a hidden window runs no animation frames
  return box;
}

export function legend(pick = false) {
  const mk = (...shapes) => s('svg', { viewBox: '0 0 22 14', 'aria-hidden': 'true' }, ...shapes);
  return h('div', { class: 'legend', 'aria-label': '노선도 읽는 법' },
    h('span', {}, mk(s('line', { class: 'track ran', x1: 0, x2: 22, y1: 7, y2: 7 }), s('circle', { class: 'st-done', cx: 11, cy: 7, r: 5 })), '끝남'),
    h('span', {}, mk(s('circle', { class: 'st-dot', cx: 11, cy: 7, r: 5 }), s('circle', { class: 'st-ring', cx: 11, cy: 7, r: 6.5 })), '진행 중'),
    h('span', {}, mk(s('circle', { class: 'st-next', cx: 11, cy: 7, r: 5.5 }), s('circle', { class: 'st-dot', cx: 11, cy: 7, r: 2 })), '다음 차례'),
    h('span', {}, mk(s('line', { class: 'track', x1: 0, x2: 22, y1: 7, y2: 7 }), s('circle', { class: 'st-planned', cx: 11, cy: 7, r: 4.5 })), '남음'),
    h('span', {}, mk(s('line', { class: 'track order', x1: 0, x2: 22, y1: 7, y2: 7 }), s('circle', { class: 'st-outline', cx: 11, cy: 7, r: 4 })), '순서만 적힘 (전제 없음)'),
    h('span', { class: 'faint' }, pick ? '역을 누르면 고름' : '역을 누르면 할 일'));
}
