// 현황판 · find: a word in every document and code file of the project (live documents first, records after),
// and the glossary of the method's and the board's words (MAP.md's own 용어 table first when it has one).
import { h, t, openDoc } from './ui.js';
import { titleRow, get } from './app.js';

const state = { q: '', result: null, words: null };

export async function searchView(ctx) {
  state.words ||= (await get('/api/glossary').catch(() => ({ words: [] }))).words;
  state.files = ctx.store.cache.files || (ctx.store.cache.files = await get('/api/files').catch(() => null));
  const input = h('input', { type: 'search', class: 'search-in', placeholder: '찾을 말 (두 글자 이상)', value: state.q, 'aria-label': '문서 본문에서 찾기', 'data-autofocus': '' });
  const results = h('div', { class: 'results', 'aria-live': 'polite' });
  const terms = h('div', { class: 'terms' });
  const paintTerms = () => {
    const q = state.q.trim();
    const list = state.words.filter(w => !q || w.word.includes(q) || w.meaning.includes(q));
    terms.replaceChildren(list.length ? h('dl', { class: 'glossary' }, list.map(w => [h('dt', {}, w.word, w.source !== '현황판' ? h('span', { class: 'pill', text: w.source }) : null), h('dd', { text: w.meaning })]))
      : h('p', { class: 'muted', text: '이 말의 풀이는 없습니다.' }));
  };
  const paint = () => {
    const r = state.result;
    if (!r || r.q.length < 2) {
      const recent = (state.files?.files || []).filter(f => f.tier === 0).sort((x, y) => y.last - x.last).slice(0, 8);
      const pad = n => String(n).padStart(2, '0');      // taste-skill-ignore: a date, as everywhere on the board
      const when = f => { const d = new Date(f.last * 1000); return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`; };
      const rows = recent.map(f => h('li', {}, h('span', { class: 't faint', text: when(f) }),
        h('a', { class: 'link', href: `#/files?p=${encodeURIComponent(f.path)}`, text: f.name }),
        h('span', { class: 'hit-t', text: f.desc || f.role })));
      results.replaceChildren(
        h('p', { class: 'muted', text: '두 글자 이상 넣으면 모든 문서와 코드의 본문에서 찾습니다. 단축키 / 로 이 화면이 열립니다.' }),
        recent.length ? h('section', { class: 'hit-file' }, h('p', { class: 'hit-h', text: '최근에 바뀐 지휘 문서' }), h('ul', { class: 'recent' }, rows)) : '');
      return;
    }
    if (!r.hits.length) { results.replaceChildren(h('p', { class: 'empty', text: `"${r.q}"이 들어간 곳이 없습니다.` })); return; }
    const groups = new Map();
    r.hits.forEach(x => { if (!groups.has(x.file)) groups.set(x.file, []); groups.get(x.file).push(x); });
    results.replaceChildren(h('p', { class: 'muted' }, t(String(r.files)), '개 파일, ', t(String(r.hits.length)), '곳', r.cut ? ' (앞의 150곳만)' : ''),
      ...[...groups].map(([file, hits]) => h('section', { class: 'hit-file' },
        h('p', { class: 'hit-h' }, h('a', { class: 'link', href: `#/files?p=${encodeURIComponent(file)}`, text: file }), h('span', { class: 'faint', text: ` ${hits.length}곳` })),
        h('ul', {}, hits.slice(0, 8).map(x => h('li', {},
          h('span', { class: 't faint', text: `${x.line}` }),
          x.heading && file.endsWith('.md') ? h('button', { class: 'ref', type: 'button', onclick: () => openDoc(file, x.heading.match(/^(\d+(?:-\d+)*)\./)?.[1] || x.heading), text: x.heading.slice(0, 40) }) : null,
          h('span', { class: 'hit-t' }, mark(x.text, r.q)))),
          hits.length > 8 ? h('li', { class: 'muted', text: `외 ${hits.length - 8}곳` }) : null))));
  };
  let timer = null;
  input.addEventListener('input', () => {
    state.q = input.value;
    paintTerms();
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = state.q.trim();
      if (q.length < 2) { state.result = null; paint(); return; }
      try { state.result = await get(`/api/search?q=${encodeURIComponent(q)}`); } catch (e) { results.replaceChildren(h('p', { class: 'error', text: e.message })); return; }
      if (state.q.trim() === q) paint();
    }, 220);
  });
  paint();
  paintTerms();
  return [...titleRow('찾기', h('p', { class: 'finding', text: '문서와 코드의 본문에서 찾고, 처음 보는 말의 풀이를 봅니다.' })),
    h('div', { class: 'search-grid', style: { marginTop: '18px' } },
      h('section', { class: 'card', 'aria-label': '본문 찾기' }, input, results),
      h('section', { class: 'card', 'aria-labelledby': 'terms-h' }, h('header', {}, h('h2', { id: 'terms-h', text: '용어 풀이' }), h('span', { class: 'meta', text: '찾을 말로 함께 거름' })), terms))];
}

function mark(text, q) {
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (i < 0) return text;
  return [text.slice(0, i), h('mark', { text: text.slice(i, i + q.length) }), text.slice(i + q.length)];
}
