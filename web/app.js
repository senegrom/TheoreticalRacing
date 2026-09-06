import {Engine} from './engine.js';
import {Board} from './board.js';

const $ = id => document.getElementById(id);
const names = ['North-west', 'North', 'North-east', 'West', 'No acceleration', 'East', 'South-west', 'South', 'South-east'];
const arrows = ['↖', '↑', '↗', '←', '·', '→', '↙', '↓', '↘'];
const colors = ['#0000ff', '#ff0000', '#00ff00', '#ffff00', '#00ffff', '#ffc800', '#808080', '#ff00ff', '#000000'];
let catalog = [], engine = null, state = null, busy = false, failed = false, paused = false, timer, generation = 0, raceName = '';
let roster = Array.from({length: 9}, (_, i) => ({name: `Player ${i + 1}`, kind: i === 0 ? 'HUMAN' : 'AI2', color: colors[i]}));
const board = new Board($('board'), p => {
  if (!state || busy || failed) return;
  if (state.phase === 'PLAY') {
    const move = [...state.moves].sort((a, b) => distance(a.position, p) - distance(b.position, p))[0];
    if (move && distance(move.position, p) * board.scale <= Math.max(20, board.scale * .6)) act('preview', move.index);
  } else if (['DRAWTRACK', 'PLACEPLAYERS'].includes(state.phase)) {
    const [x, y] = p.map(Math.round);
    $('place-x').value = x; $('place-y').value = y;
    if (x >= 0 && y >= 0 && x <= state.cols && y <= state.rows) act('click', x, y);
  }
}, p => { $('coordinates').textContent = `X ${Math.round(p[0])} · Y ${Math.round(p[1])}   /   Drag to pan`; });
const preview = new Board($('track-preview'));
const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

function notice(text = '') { $('notice').textContent = text; $('notice').hidden = !text; }
function human() { return state?.phase === 'PLAY' && state.players[state.current]?.kind === 'HUMAN'; }
function modalOpen() { return $('setup').open || $('instructions').open; }
function schedule() {
  clearTimeout(timer);
  if (!engine || !state || busy || failed || modalOpen() || document.hidden || state.phase === 'FINISHED') return;
  const ai = state.phase === 'PLAY' && !human();
  if (!state.ready || (ai && !paused)) {
    timer = setTimeout(() => act('tick'), !state.ready ? 400 : Number($('speed').value));
  }
}
function accept(next) {
  const old = state;
  state = next;
  if (next.failure) { failed = true; notice(`Engine error: ${next.failure}. No replacement AI has been substituted. Start a new race to recover.`); }
  else if (next.messages?.length) notice(next.messages.join(' '));
  else if (old?.turn !== next.turn) notice();
  board.set(next);
  if (!old || (old.phase !== 'PLAY' && next.phase === 'PLAY')) board.focus();
  render();
}
async function act(method, ...args) {
  if (!engine || busy || failed) return;
  const current = engine, token = generation;
  busy = true; clearTimeout(timer); render();
  try {
    const next = await current.call(method, ...args);
    if (token === generation) accept(next);
  } catch (error) {
    if (token === generation && error.name !== 'AbortError') {
      failed = true;
      notice(`${error.message} Start a new race to recover.`);
    }
  } finally {
    if (token === generation) { busy = false; render(); schedule(); }
  }
}
function render() {
  const s = state;
  $('export').disabled = !s || busy || failed || s.turn === 0;
  if (!s) return;
  document.body.dataset.phase = s.phase;
  document.body.dataset.turn = s.turn;
  document.body.classList.toggle('loading', !s.ready);
  const driver = s.players[s.current];
  const phaseNames = {START: 'Your blank canvas', DRAWTRACK: 'Draw the circuit', PLACEPLAYERS: 'On the starting grid', PLAY: 'Race in progress', FINISHED: 'Chequered flag'};
  $('phase').textContent = phaseNames[s.phase] ?? s.phase;
  $('race-meta').textContent = `${s.players.length} drivers · ${s.laps} ${s.laps === 1 ? 'lap' : 'laps'} · turn ${s.turn}`;
  $('grid-label').textContent = `${s.cols} × ${s.rows} grid`;
  $('driver').textContent = s.phase === 'FINISHED' ? 'Race complete' : driver?.name ?? 'Ready to race';
  $('status').textContent = !s.ready ? 'Building the original reachability maps…' : busy ? 'Engine working…' : s.status;
  $('telemetry').textContent = s.phase === 'PLAY' && driver ? `Position ${driver.position.join(', ')}  ·  Velocity ${driver.velocity.join(', ')}` : '';
  $('placement').hidden = !['DRAWTRACK', 'PLACEPLAYERS'].includes(s.phase) || (s.phase === 'PLACEPLAYERS' && s.current >= s.players.length);
  $('place-x').max = s.cols; $('place-y').max = s.rows;
  $('place').disabled = busy || failed;
  $('first-start').hidden = s.phase !== 'PLACEPLAYERS';
  $('first-start').disabled = busy || failed || !s.starts.length;
  $('moves').hidden = !human();
  for (const button of $('moves').children) {
    const index = Number(button.dataset.index), move = s.moves.find(m => m.index === index);
    button.disabled = busy || failed || !human();
    button.dataset.legal = move ? String(move.legal) : '';
    button.setAttribute('aria-pressed', String(s.selected === index));
    button.setAttribute('aria-label', names[index] + (move ? `: to ${move.position.join(', ')}, ${move.legal ? move.finishes ? 'finish' : 'legal' : 'crash'}` : ''));
    button.lastElementChild.textContent = move && !move.legal ? '×' : '';
  }
  const chosen = s.moves.find(m => m.index === s.selected);
  $('move-detail').textContent = chosen ? `To (${chosen.position.join(', ')}) · velocity (${chosen.velocity.join(', ')}) · ${chosen.timeout ? 'race turn limit reached' : !chosen.legal ? 'crash' : chosen.finishes ? 'finish' : chosen.lap ? 'lap crossing' : 'legal move'}` : human() ? 'Select an acceleration, then confirm.' : 'Each move is decided by the original Java engine.';
  $('confirm').hidden = !human();
  $('confirm').disabled = busy || failed || !chosen;
  $('confirm').classList.toggle('danger', Boolean(chosen && !chosen.legal));
  $('confirm').textContent = chosen && !chosen.legal ? 'Confirm crash…' : 'Confirm move';
  $('ok').hidden = !s.ok || s.phase === 'PLAY' || s.phase === 'FINISHED';
  $('ok').disabled = busy || failed || (s.phase === 'PLACEPLAYERS' && !s.ready);
  $('ok').textContent = s.phase === 'START' ? 'Begin drawing' : s.phase === 'DRAWTRACK' ? (s.current === 0 ? 'Left border done →' : 'Complete track →') : 'Start race →';
  $('undo').disabled = busy || failed || !s.undo;
  $('pause').disabled = failed || s.phase !== 'PLAY';
  $('pause').textContent = paused ? 'Resume AI' : 'Pause AI';
  $('step').disabled = busy || failed || !s.ready || !paused || s.phase !== 'PLAY' || human();
  $('standings').replaceChildren(...s.players.map((p, i) => {
    const li = document.createElement('li');
    li.classList.toggle('current', s.phase === 'PLAY' && i === s.current);
    const badge = document.createElement('span'); badge.className = 'badge'; badge.style.backgroundColor = p.color;
    const label = document.createElement('span'); label.className = 'name'; label.textContent = p.name;
    const kind = document.createElement('small'); kind.textContent = `${i + 1} · ${p.kind === 'HUMAN' ? 'Human' : p.kind}`; label.append(kind);
    const result = document.createElement('span'); result.className = 'result';
    result.textContent = p.place > 0 ? `P${p.place}` : p.place < 0 ? 'Crashed' : p.position[0] < -1000 ? 'To place' : s.laps > 1 ? `Lap ${Math.min(p.lap + 1, s.laps)}/${s.laps}` : 'Racing';
    li.append(badge, label, result); return li;
  }));
}
for (let i = 0; i < 9; i++) {
  const b = document.createElement('button'); b.dataset.index = i; b.textContent = arrows[i]; b.disabled = true;
  b.append(document.createElement('small')); b.addEventListener('click', () => act('preview', i)); $('moves').append(b);
}
$('confirm').addEventListener('click', () => {
  const move = state?.moves.find(m => m.index === state.selected);
  if (!move || busy) return;
  const confirmed = !move.legal && window.confirm('This move crashes your car. Take it anyway?');
  if (!move.legal && !confirmed) return;
  act('move', move.index, confirmed);
});
$('ok').addEventListener('click', () => act('ok'));
$('undo').addEventListener('click', () => act('undo'));
$('place').addEventListener('click', () => {
  const x = Number($('place-x').value), y = Number($('place-y').value);
  if (state && Number.isInteger(x) && Number.isInteger(y) && x >= 0 && y >= 0 && x <= state.cols && y <= state.rows) act('click', x, y);
  else notice('Enter grid coordinates within the track dimensions.');
});
$('first-start').addEventListener('click', () => { if (state?.starts.length) act('click', ...state.starts[0]); });
$('pause').addEventListener('click', () => { paused = !paused; render(); schedule(); });
$('step').addEventListener('click', () => act('tick'));
$('speed').addEventListener('change', schedule);
$('fit').addEventListener('click', () => board.fit());
$('focus-car').addEventListener('click', () => board.focus());
$('zoom-in').addEventListener('click', () => board.zoom(1.4));
$('zoom-out').addEventListener('click', () => board.zoom(1 / 1.4));
$('new-race').addEventListener('click', () => { clearTimeout(timer); $('setup').showModal(); preview.fit(); });
$('close-setup').addEventListener('click', () => $('setup').close());
$('setup').addEventListener('close', schedule);
$('help').addEventListener('click', () => { clearTimeout(timer); $('instructions').showModal(); });
$('close-help').addEventListener('click', () => $('instructions').close());
$('instructions').addEventListener('close', schedule);
document.addEventListener('visibilitychange', schedule);
window.addEventListener('pagehide', () => { clearTimeout(timer); engine?.destroy(); });
window.addEventListener('pageshow', event => { if (event.persisted) { engine = null; failed = true; notice('The engine was closed when you left this page. Start a new race.'); render(); } });
window.addEventListener('keydown', e => {
  if (e.repeat || e.ctrlKey || e.altKey || e.metaKey || modalOpen() || (/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName) || (e.target.tagName === 'BUTTON' && !e.target.closest('#moves')))) return;
  const map = {q:0,w:1,e:2,a:3,s:4,d:5,z:6,x:7,c:8,ArrowUp:1,ArrowLeft:3,ArrowRight:5,ArrowDown:7,' ':4};
  const keypad = {Numpad7:0,Numpad8:1,Numpad9:2,Numpad4:3,Numpad5:4,Numpad6:5,Numpad1:6,Numpad2:7,Numpad3:8};
  const index = keypad[e.code] ?? map[e.key];
  if (index !== undefined && human()) { e.preventDefault(); act('preview', index); }
  else if (e.key === 'Enter') { e.preventDefault(); if (human()) $('confirm').click(); else if (!$('ok').hidden) $('ok').click(); }
  else if (e.key.toLowerCase() === 'u') { e.preventDefault(); $('undo').click(); }
});
$('export').addEventListener('click', async () => {
  if (!engine || busy) return;
  const current = engine;
  busy = true; render();
  try {
    const text = await current.call('log');
    const url = URL.createObjectURL(new Blob([text], {type: 'text/plain;charset=utf-8'}));
    const a = document.createElement('a'); a.href = url; a.download = 'theoretical-racing.log'; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  } catch (e) { if (e.name !== 'AbortError') notice(e.message); }
  finally { if (current === engine) { busy = false; render(); schedule(); } }
});
function readRoster() {
  for (const [i, row] of [...$('roster').children].entries()) {
    roster[i] = {name: row.querySelector('[data-name]').value, kind: row.querySelector('select').value, color: row.querySelector('[type=color]').value};
  }
}
function drawRoster() {
  readRoster();
  const count = Math.max(1, Math.min(9, Number($('player-count').value) || 1));
  $('roster').replaceChildren(...roster.slice(0, count).map((p, i) => {
    const row = document.createElement('div'); row.className = 'roster-row';
    const n = document.createElement('span'); n.textContent = String(i + 1).padStart(2, '0');
    const name = document.createElement('input'); name.value = p.name; name.maxLength = 40; name.dataset.name = ''; name.setAttribute('aria-label', `Driver ${i + 1} name`);
    const kind = document.createElement('select'); kind.setAttribute('aria-label', `Driver ${i + 1} type`);
    for (const [value, label] of [['HUMAN', 'Human'], ['AI1', 'AI1'], ['AI2', 'AI2']]) kind.add(new Option(label, value));
    kind.value = p.kind;
    const color = document.createElement('input'); color.type = 'color'; color.value = p.color; color.setAttribute('aria-label', `Driver ${i + 1} colour`);
    row.append(n, name, kind, color); return row;
  }));
}
$('player-count').addEventListener('input', drawRoster);
function updateTrack() {
  const t = catalog.find(t => t.id === $('track').value);
  $('custom-size').hidden = Boolean(t);
  const drawing = {cols: Number($('cols').value), rows: Number($('rows').value)};
  preview.set(t ?? drawing); preview.fit();
  $('track-info').textContent = t ? `${t.cols} × ${t.rows} grid · ${t.left.length + t.right.length} original border points${t.lapClosable ? ' · loop circuit' : ''}` : 'Draw both borders on the grid after starting.';
}
$('track').addEventListener('change', updateTrack);
$('cols').addEventListener('input', updateTrack); $('rows').addEventListener('input', updateTrack);
const property = value => String(value).replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t').replace(/ /g, '\\ ');
$('setup-form').addEventListener('submit', async e => {
  e.preventDefault();
  if (!$('setup-form').reportValidity()) return;
  const seed = $('seed').value.trim();
  try { if (seed && (!/^-?\d+$/.test(seed) || BigInt(seed) < -(2n ** 63n) || BigInt(seed) > 2n ** 63n - 1n)) throw new Error(); }
  catch { $('setup-error').textContent = 'The seed must be a signed 64-bit integer, or left blank.'; return; }
  readRoster();
  const count = Number($('player-count').value), track = $('track').value;
  const config = {nPlayers: count, laps: Number($('laps').value), gameX: Number($('cols').value), gameY: Number($('rows').value)};
  roster.slice(0, count).forEach((p, i) => {
    config[`player${i + 1}Name`] = p.name || `Player ${i + 1}`;
    config[`player${i + 1}Kind`] = p.kind;
    config[`player${i + 1}Color`] = [1, 3, 5].map(j => parseInt(p.color.slice(j, j + 2), 16)).join(' ');
  });
  try { localStorage.setItem('theoretical-racing-setup-v1', JSON.stringify({track, count, laps: config.laps, seed, roster})); } catch { /* Private browsing must not prevent play. */ }
  clearTimeout(timer); engine?.destroy();
  const token = ++generation;
  busy = true; failed = false; state = null; paused = false;
  $('setup-error').textContent = ''; $('setup').close(); notice();
  raceName = catalog.find(t => t.id === track)?.name ?? 'Your circuit'; $('track-title').textContent = raceName;
  board.set(catalog.find(t => t.id === track) ?? {cols: config.gameX, rows: config.gameY}); board.fit();
  $('driver').textContent = 'Preparing your race'; $('status').textContent = 'Loading the Java runtime…';
  $('phase').textContent = 'Preparing the engine'; document.body.dataset.phase = 'LOADING';
  for (const button of document.querySelectorAll('.pitwall button')) button.disabled = true;
  const current = new Engine(text => { if (token === generation) $('status').textContent = text; }); engine = current;
  try {
    const properties = Object.entries(config).map(([k, v]) => `${k}=${property(v)}`).join('\n');
    const next = await current.call('create', track, properties, seed);
    if (token !== generation) return;
    accept(next);
  } catch (error) {
    if (token === generation && error.name !== 'AbortError') {
      failed = true; $('status').textContent = 'The engine could not start.'; notice(error.message); current.destroy();
    }
  } finally { if (token === generation) { busy = false; render(); schedule(); } }
});
async function init() {
  if (!/^https?:$/.test(location.protocol)) throw new Error('Serve this app over HTTP or HTTPS, not by opening index.html as a file.');
  const response = await fetch(new URL('./tracks.json', import.meta.url));
  if (!response.ok) throw new Error('Track catalogue is missing. Run web/build.sh and serve web/dist.');
  catalog = await response.json();
  $('track').replaceChildren(...catalog.map(t => new Option(t.name, t.id)), new Option('Draw a custom circuit', ''));
  $('track').value = 'silverstone';
  try {
    const saved = JSON.parse(localStorage.getItem('theoretical-racing-setup-v1'));
    if (saved && Array.isArray(saved.roster) && saved.roster.length === 9) {
      roster = roster.map((p, i) => {
        const r = saved.roster[i];
        return r && typeof r.name === 'string' && ['HUMAN', 'AI1', 'AI2'].includes(r.kind) && /^#[0-9a-f]{6}$/i.test(r.color) ? {...r, name: r.name.slice(0, 40)} : p;
      });
      if (catalog.some(t => t.id === saved.track) || saved.track === '') $('track').value = saved.track;
      if (Number.isInteger(saved.count) && saved.count >= 1 && saved.count <= 9) $('player-count').value = saved.count;
      if (Number.isInteger(saved.laps) && saved.laps >= 1 && saved.laps <= 99) $('laps').value = saved.laps;
      if (typeof saved.seed === 'string') $('seed').value = saved.seed.slice(0, 20);
    }
  } catch { /* Invalid or inaccessible settings are ignored. */ }
  $('track').disabled = false; $('start').disabled = false;
  drawRoster(); updateTrack();
  board.set(catalog.find(t => t.id === $('track').value) ?? {cols: 86, rows: 48});
  $('setup').showModal();
}
init().catch(error => { notice(error.message); $('setup-error').textContent = error.message; });
