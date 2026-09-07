import {Engine} from './engine.js?v=6';
import {Activity} from './activity.js?v=7';
import {Board} from './board.js?v=6';

const $ = id => document.getElementById(id);
const names = ['North-west', 'North', 'North-east', 'West', 'No acceleration', 'East', 'South-west', 'South', 'South-east'];
const arrows = ['↖', '↑', '↗', '←', '·', '→', '↙', '↓', '↘'];
const colors = ['#0000ff', '#ff0000', '#00ff00', '#ffff00', '#00ffff', '#ffc800', '#808080', '#ff00ff', '#000000'];
let catalog = [], engine = null, state = null, busy = false, polling = false, failed = false, paused = false, timer, generation = 0, raceName = '';
let operation = '', preparation = null, bootStatus = '';
const activity = new Activity($('work-status'));
let roster = Array.from({length: 9}, (_, i) => ({name: `Player ${i + 1}`, kind: i === 0 ? 'HUMAN' : 'AI2', color: colors[i]}));
const board = new Board($('board'), p => {
  if (!state || busy || failed) return;
  if (state.phase === 'PLAY') {
    const move = [...state.moves].sort((a, b) => distance(a.position, p) - distance(b.position, p))[0];
    if (move && distance(move.position, p) * board.scale <= Math.max(20, board.scale * .6)) act('preview', move.index);
  } else if (state.phase === 'DRAWTRACK' || (state.phase === 'PLACEPLAYERS' && state.players[state.current]?.kind === 'HUMAN')) {
    const [x, y] = p.map(Math.round);
    $('place-x').value = x; $('place-y').value = y;
    if (x >= 0 && y >= 0 && x <= state.cols && y <= state.rows) act('click', x, y);
  }
}, p => { $('coordinates').textContent = `X ${Math.round(p[0])} · Y ${Math.round(p[1])}   /   Drag to pan`; });
const preview = new Board($('track-preview'));
const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

function notice(text = '') { $('notice-text').textContent = text; $('notice').hidden = !text; }
$('keep-waiting').addEventListener('click', () => engine?.keepWaiting());
$('dismiss-notice').addEventListener('click', () => notice());
function human() { return state?.phase === 'PLAY' && state.players[state.current]?.kind === 'HUMAN'; }
function modalOpen() { return $('setup').open || $('instructions').open || $('installation').open; }
function schedule() {
  clearTimeout(timer);
  if (!engine || !state || busy || polling || failed || modalOpen() || document.hidden || state.phase === 'FINISHED') return;
  const ai = state.phase === 'PLAY' && !human();
  const placingAi = state.phase === 'PLACEPLAYERS' && state.players[state.current]?.kind !== 'HUMAN' && state.current < state.players.length;
  if (!state.ready || placingAi || (ai && !paused)) {
    timer = setTimeout(state.ready ? () => act('tick') : pollReadiness, !state.ready ? 400 : Number($('speed').value));
  }
}
async function pollReadiness() {
  if (!engine || busy || polling || failed) return;
  const current = engine, token = generation;
  polling = true;
  try {
    // A tiny readiness probe avoids repeatedly serializing the whole track,
    // rescanning start cells and redrawing histories while Java is computing.
    const ready = await current.call('readiness');
    if (token !== generation) return;
    if (ready.failure) throw new Error(ready.failure);
    if (ready.ready) {
      const next = await current.call('snapshot');
      if (token === generation) accept(next);
    }
  } catch (error) {
    if (token === generation && error.name !== 'AbortError') {
      failed = true; current.destroy(); notice(`${error.message} Start a new race to recover.`);
    }
  } finally {
    if (token === generation) { polling = false; render(); schedule(); }
  }
}
const warnBeforeLeave = event => { event.preventDefault(); event.returnValue = ''; };
function accept(next) {
  const old = state;
  state = next;
  window.removeEventListener('beforeunload', warnBeforeLeave);
  if (next.phase !== 'FINISHED') window.addEventListener('beforeunload', warnBeforeLeave);
  if (next.failure) { failed = true; notice(`Engine error: ${next.failure}. No replacement AI has been substituted. Start a new race to recover.`); }
  else if (next.phase === 'FINISHED') notice();
  else if (next.messages?.length) notice(next.messages.join(' '));
  else if (old?.turn !== next.turn) notice();
  board.set(next);
  const driver = next.players[next.current];
  if (next.phase === 'FINISHED' && old?.phase !== 'FINISHED') board.fit();
  else if (!old && next.phase === 'PLACEPLAYERS' && driver?.kind === 'HUMAN') board.focus();
  else if (next.phase === 'PLAY' && driver?.kind === 'HUMAN') {
    const [x, y] = board.screen(driver.position);
    if (old?.phase !== 'PLAY' || (!board.fitMode && (x < 20 || y < 20 || x > board.width - 20 || y > board.height - 20))) board.focus();
  }
  render();
}
async function act(method, ...args) {
  if (!engine || busy || failed) return;
  const current = engine, token = generation;
  busy = true; operation = method;
  if (method === 'ok') preparation = null;
  clearTimeout(timer); render();
  try {
    const next = await current.call(method, ...args);
    if (token === generation) accept(next);
  } catch (error) {
    if (token === generation && error.name !== 'AbortError') {
      failed = true; current.destroy();
      notice(`${error.message} Start a new race to recover.`);
    }
  } finally {
    if (token === generation) { busy = false; render(); schedule(); }
  }
}
function renderWork() {
  if (!engine || state?.phase === 'FINISHED') { activity.hide(); return; }
  const preparing = !state || ['START', 'DRAWTRACK', 'PLACEPLAYERS'].includes(state.phase);
  const plan = ['START', 'DRAWTRACK'].includes(state?.phase) && !preparation?.stage ? {stage:1, stages:6} : preparation;
  activity.setPreparation(preparing, plan, state?.phase === 'PLACEPLAYERS' && state.ready && !failed);
  if (failed) { activity.idle('Engine stopped', 'Start a new race to recover.'); return; }
  if (!state) {
    activity.show(`startup-${generation}`, 'Preparing your race', preparation || {phase: bootStatus || 'Loading the Java runtime…'});
  } else if (!state.ready) {
    activity.show(`startup-${generation}`, 'Building shared track maps', preparation);
  } else if (busy) {
    const driver = state.players[state.current];
    const label = operation === 'tick' && !human() ? `${driver?.name || 'AI'} is thinking…` :
      ({preview:'Calculating move preview…', move:'Applying your move…', undo:'Restoring your turn…',
        ok:'Preparing the race…', click:'Updating the track…', log:'Preparing race log…'})[operation] || 'Engine working…';
    activity.show(`action-${generation}-${state.turn}-${operation}`, label,
      preparation && operation === 'ok' ? preparation : {phase: operation === 'tick' ? 'Evaluating the original AI search. Remaining work is unknown.' : 'Waiting for the original Java engine.'});
  } else if (state.phase === 'PLACEPLAYERS' && state.players[state.current]?.kind !== 'HUMAN' && state.current < state.players.length) {
    activity.show(`placement-${generation}-${state.current}`, `${state.players[state.current].name} · choosing starting cell`,
      {phase: 'Scoring free cells using completed maps and cars already placed.'});
  } else if (state.phase === 'PLAY' && !human() && !paused) {
    // Include the pacing gap in the AI-turn slot rather than flashing it off.
    activity.show(`action-${generation}-${state.turn}-tick`, `${state.players[state.current].name} · AI turn`,
      {phase: 'Next move will begin after the selected pacing delay.'});
  } else {
    const label = state.phase === 'PLAY' ? (paused ? 'AI paused' : 'Ready') : state.phase === 'PLACEPLAYERS' ? 'Track maps ready' : 'Draw your circuit';
    const detail = state.phase === 'PLAY' ? (paused ? 'Choose Step or Resume AI.' : 'Engine ready.') : state.phase === 'PLACEPLAYERS' ? 'Maps are shared by all drivers. Finish placing cars, then start.' : 'Preparation starts when both borders are confirmed.';
    activity.idle(label, detail);
  }
}
function render() {
  const s = state;
  const exportDisabled = !s || busy || failed || s.turn === 0;
  $('export').disabled = exportDisabled; $('more-export').disabled = exportDisabled;
  renderWork();
  document.querySelector('.decision').setAttribute('aria-busy', String(busy));
  if (!s) return;
  document.body.dataset.phase = s.phase;
  document.body.dataset.turn = s.turn;
  document.body.classList.toggle('loading', !s.ready);
  const driver = s.players[s.current];
  const phaseNames = {START: 'Your blank canvas', DRAWTRACK: 'Draw the circuit', PLACEPLAYERS: 'On the starting grid', PLAY: 'Race in progress', FINISHED: 'Chequered flag'};
  $('phase').textContent = phaseNames[s.phase] ?? s.phase;
  $('race-meta').textContent = `${s.players.length} drivers · ${s.laps} ${s.laps === 1 ? 'lap' : 'laps'} · turn ${s.turn}`;
  $('grid-label').textContent = `${s.cols} × ${s.rows} grid`;
 $('driver').textContent = s.phase === 'FINISHED' ? 'Final classification' : s.phase === 'START' ? 'Draw your circuit' : s.phase === 'DRAWTRACK' ? (s.current === 0 ? 'Left border' : 'Right border') : driver?.name ?? 'Ready to race';
  $('status').textContent = failed ? 'The engine stopped. Start a new race to recover.' : s.phase === 'FINISHED' ? 'Race complete. Save the log or start another race.' : !s.ready ? 'Building the original reachability maps…' : paused && s.phase === 'PLAY' && !human() ? (busy ? 'Pausing after the current AI move…' : 'AI paused. Choose Step or Resume AI.') : s.status;
  $('driver').title = $('driver').textContent;
  $('status').title = $('status').textContent;
  $('telemetry').textContent = s.phase === 'PLAY' && driver ? `Position ${driver.position.join(', ')}  ·  Velocity ${driver.velocity.join(', ')}` : s.phase === 'DRAWTRACK' ? `${(s.current === 0 ? s.left : s.right).length} border points` : '';
  $('placement').hidden = !['DRAWTRACK', 'PLACEPLAYERS'].includes(s.phase) || (s.phase === 'PLACEPLAYERS' && s.current >= s.players.length);
  $('place-x').max = s.cols; $('place-y').max = s.rows;
  const placingAi = s.phase === 'PLACEPLAYERS' && driver?.kind !== 'HUMAN';
  $('place').disabled = busy || failed || placingAi;
  $('first-start').hidden = s.phase !== 'PLACEPLAYERS';
  $('first-start').disabled = busy || failed || placingAi || !s.starts.length;
  document.querySelector('.decision').classList.toggle('driving', s.phase === 'PLAY');
  document.querySelector('.decision').classList.toggle('finished', s.phase === 'FINISHED');
  $('decision-eyebrow').textContent = s.phase === 'FINISHED' ? 'Results' : 'At the wheel';
  $('finish-actions').hidden = s.phase !== 'FINISHED';
  $('finish-export').disabled = exportDisabled;
  $('finish-new').disabled = false;
  $('moves').hidden = s.phase !== 'PLAY';
  for (const button of $('moves').children) {
    const index = Number(button.dataset.index), move = s.moves.find(m => m.index === index);
    button.disabled = busy || failed || !human();
    button.dataset.legal = move ? String(move.legal) : '';
    button.setAttribute('aria-pressed', String(s.selected === index));
    button.setAttribute('aria-label', names[index] + (move ? `: to ${move.position.join(', ')}, ${move.legal ? move.finishes ? 'finish' : 'legal' : 'crash'}` : ''));
    button.lastElementChild.textContent = move && !move.legal ? '×’ : '';
  }
  const chosen = s.moves.find(m => m.index === s.selected);
  $('move-detail').textContent = chosen ? `To (${chosen.position.join(', ')}) · velocity (${chosen.velocity.join(', ')}) · ${chosen.timeout ? 'race turn limit reached' : !chosen.legal ? 'crash' : chosen.finishes ? 'finish' : chosen.lap ? 'lap crossing' : 'legal move'}` : human() ? 'Select an acceleration, then confirm.' : 'Each move is decided by the original Java engine.';
  $('confirm').hidden = s.phase !== 'PLAY';
  $('confirm').disabled = busy || failed || !human() || !chosen;
  $('confirm').classList.toggle('danger', Boolean(chosen && !chosen.legal));
  $('confirm').textContent = !human() && s.phase === 'PLAY' ? 'AI driving : chosen && !chosen.legal ? 'Confirm crash…' : 'Confirm move';
  $('ok').hidden = !s.ok || s.phase === 'PLAY' || s.phase === 'FINISHED';
  $('ok').disabled = busy || failed || (s.phase === 'PLACEPLAYERS' && !s.ready);
  $('ok').textContent = s.phase === 'START' ? 'Begin drawing' : s.phase === 'DRAWTRACK' ? (s.current === 0 ? 'Left border done →' : 'Complete track →') : 'Start race →';
  const undoLabel = s.phase === 'DRAWTRACK' ? 'Undo point' : s.phase === 'PLACEPLAYERS' ? 'Undo placement' : 'Undo turn';
  $('undo').disabled = busy || failed || !s.undo;
  $('undo').textContent = matchMedia('(max-width: 360px)').matches ? 'Undo' : undoLabel;
  $('undo').setAttribute('aria-label', undoLabel);
  $('pause').disabled = failed || s.phase !== 'PLAY';
  const pauseLabel = paused ? 'Resume AI' : 'Pause AI';
  $('pause').textContent = matchMedia('(max-width: 360px)').matches ? (paused ? 'Resume' : 'Pause') : pauseLabel;
  $('pause').setAttribute('aria-label', pauseLabel);
  $('pause').title = paused && busy && operation === 'tick' ? 'Pauses after the current move completes' : pauseLabel;
  $('step').disabled = busy || failed || !s.ready || !paused || s.phase !== 'PLAY' || human();
  $('step').setAttribute('aria-label', 'Step AI once');
  renderStandings(s);
}
function renderStandings(s) {
  if ($('standings').children.length !== s.players.length) $('standings').replaceChildren(...s.players.map(() => {
    const row = document.createElement('li');
    row.innerHTML = '<span class="badge"></span><span class="name"><span></span><small></small></span><span class="result"></span>';
    return row;
  }));
  s.players.forEach((p, i) => {
    const li = $('standings').children[i];
    li.classList.toggle('current', s.phase === 'PLAY' && i === s.current);
    const badge = li.querySelector('.badge'); badge.style.backgroundColor = p.color;
    const label = li.querySelector('.name'); label.firstElementChild.textContent = p.name;
    const kind = label.querySelector('small'); kind.textContent = `${i + 1} · ${p.kind === 'HUMAN' ? 'Human' : p.kind}`;
    const result = li.querySelector('.result');
    result.textContent = p.place > 0 ? `P${p.place} · ${p.outcome === 'CRASH' ? 'Crashed' : p.outcome === 'TIMEOUT' ? 'Retired' : p.outcome === 'FINISH' ? 'Finished' : 'Classified'}` : p.position[0] < -1000 ? 'To place' : s.phase === 'PLACEPLAYERS' ? 'On grid' : s.laps > 1 ? `Lap ${Math.min(p.lap + 1, s.laps)}/${s.laps}` : 'Racing';
    label.title = p.name;
    li.dataset.outcome = p.outcome ?? '';
    result.title = result.textContent;
  });
}
for (let i = 0; i < 9; i++) {
  const b = document.createElement('button'); b.dataset.index = i; b.textContent = arrows[i]; b.disabled = true;
  b.append(document.createElement('small')); b.addEventListener('click', () => act('preview', i)); $('moves').append(b);
}
$('confirm').addEventListener('click', () => {
  const move = state?.moves.find(m => m.index === state.selected);
  if (!move) return;
  if (!move.legal && !window.confirm('This move crashes the car. Make the crash move?')) return;
  act('move');
});
$('undo').addEventListener('click', () => act('undo'));
$('ok').addEventListener('click', () => act('ok'));
$('speed').addEventListener('change', schedule);
$('pause').addEventListener('click', () => { paused = !paused; render(); schedule(); });
$('step').addEventListener('click', () => act('tick'));
$('place').addEventListener('click', () => {
  const x = $('place-x').valueAsNumber, y = $('place-y').valueAsNumber;
  if (Number.isInteger(x) && Number.isInteger(y)) act('click', x, y);
});
$('first-start').addEventListener('click', () => {
  if (state?.starts[4]) act('click', ...state.starts[4]); else if (state?.starts[0]) act('click', ...state.starts[0]);
});
$('zoom-in').addEventListener('click', () => board.zoom(1.25)); $('zoom-out').addEventListener('click', () => board.zoom(.8));
$('fit').addEventListener('click', () => board.fit()); $('focus-car').addEventListener('click', () => board.focus());

function isTypingTarget(target) { return ['INPUT','TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable; }
document.addEventListener('keydown', e => {
  if (modalOpen() || isTypingTarget(e.target)) return;
  const key = e.key.toLowerCase();
  if (key === 'u' && state?.undo && !busy && !failed) { e.preventDefault(); act('undo'); return; }
  if (!human() || busy || failed) return;
  const keys = {q:0, w:1, e:2, a:3, s:4, d:5, z:6, x:7, c:8, '7':0, '8':1, '9':2, '4':3, '5':4, '6':5, '1':6, '2':7, '3':8, ' ':4};
  const arrowsMap = {ArrowUp:1, ArrowLeft:3, ArrowRight:5, ArrowDown:7};
  const i = key === 'Enter' ? null : (e.key in arrowsMap ? arrowsMap[e.key] : keys[key]);
  if (key === 'Enter' && state.selected != null) { e.preventDefault(); $('confirm').click(); }
  else if (i != null && i != undefined) { e.preventDefault(); act('preview', i); }
});
$('new-race').addEventListener('click', () => {
  $('header-more').open = false;
  if (!state || state.phase === 'FINISHED' || window.confirm('Replace the current race? Its progress is not saved.')) $('setup').showModal();
});
$('finish-new').addEventListener('click', () => $('new-race').click());
$('help').addEventListener('click', () => $('instructions').showModal());
$('install').addEventListener('click', () => $('installation').showModal());
$('more-install').addEventListener('click', () => { $('header-more').open = false; $('installation').showModal(); });
$('close-setup').addEventListener('click', () => $('setup').close());
$('close-help').addEventListener('click', () => $('instructions').close());
$('close-install').addEventListener('click', () => $('installation').close());

function readRoster() {
  for (const [row, p] of [...$('roster').children].map((r, i) => [r, roster[i]])) {
    p.name = row.querySelector('input[data-name]').value.trim() || p.name;
    p.kind = row.querySelector('select').value;
    p.color = row.querySelector('input[type=color]').value;
  }
}
function drawRoster() {
  const count = Math.max(1, Math.min(9, Number($('player-count').value) || 1));
  $('roster').replaceChildren(...roster.slice(0, count).map((p, i) => {
    const row = document.createElement('div'); row.className = 'roster-row';
    const n = document.createElement('span'); n.textContent = String(i + 1).padStart(2, '0');
    const name = document.createElement('input'); name.value = p.name; name.maxLength = 40; name.dataset.name = ''; name.setAttribute('aria-label', `Driver ${i + 1} name`);
    const kind = document.createElement('select'); kind.setAttribute('aria-label', `Driver ${i + 1} type`);
    for (const [value, label] of [['HUMAN', 'Human'], ['AI1', 'AI1',], ['AI2', 'AI2']]) kind.add(new Option(label, value));
    kind.value = p.kind;
    const color = document.createElement('input'); color.type = 'color'; color.value = p.color; color.setAttribute('aria-label', `Driver ${i + 1} color`);
    row.append(n, name, kind, color); return row;
  }));
  }
$('player-count').addEventListener('input', drawRoster);
function validDimension(id, fallback) {
  const value = $(id).valueAsNumber;
  return Number.isInteger(value) && value >= 2 && value <= 500 ? value : fallback;
}
function updateTrack() {
  const t = catalog.find(t => t.id === $('track').value);
  $('custom-size').hidden = Boolean(t);
  $('cols').disabled = Boolean(t); $('rows').disabled = Boolean(t);
  const drawing = {cols: validDimension('cols', 86), rows: validDimension('rows', 48)};
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
  const config = {aiStartPlacement: $('ai-start-policy').value, nPlayers: count, laps: Number($('laps').value), gameX: validDimension('cols', 86), gameY: validDimension('rows', 48)};
  if (state && state.phase !== 'FINISHED' && !window.confirm('Replace the current race? Its progress is not saved.')) return;
  roster.slice(0, count).forEach((p, i) => {
    config[`player${i + 1}Name`] = p.name || `Player ${i + 1}`;
    config[`player${i + 1}Kind`] = p.kind;
    config[`player${i + 1}Color`] = [1, 3, 5].map(j => parseInt(p.color.slice(j, j + 2), 16)).join(' ');
  });
  try { localStorage.setItem('theoretical-racing-setup-v1', JSON.stringify({aiStartPlacement: config.aiStartPlacement, track, count, laps: config.laps, cols: config.gameX, rows: config.gameY, seed, roster})); } catch { /* Private browsing must not prevent play. */ }
  clearTimeout(timer); engine?.destroy();
  const token = ++generation;
  $('moves').hidden = true; $('placement').hidden = true; $('ok').hidden = true; $('confirm').hidden = true;
  $('telemetry').textContent = ''; $('standings').replaceChildren(); $('move-detail').textContent = 'Preparing the original engine…';
  document.body.classList.remove('loading');
  document.querySelector('.decision').classList.remove('driving', 'finished');
  busy = true; polling = false; failed = false; state = null; paused = false;
  operation = 'create'; preparation = null; bootStatus = 'Loading the Java runtime…'; activity.hide();
  $('setup-error').textContent = ''; $('setup').close(); notice();
  raceName = catalog.find(t => t.id === track)?.name ?? 'Your circuit'; $('track-title').textContent = raceName;
  board.set(catalog.find(t => t.id === track) ?? {cols: config.gameX, rows: config.gameY}); board.fit();
  $('driver').textContent = 'Preparing your race'; $('status').textContent = 'Loading the Java runtime…';
  $('phase').textContent = 'Preparing the engine'; document.body.dataset.phase = 'LOADING';
  for (const button of document.querySelectorAll('.pitwall button')) button.disabled = true;
  $('export').disabled = true; $('more-export').disabled = true; document.body.dataset.turn = '0';
  const current = new Engine((text, progress) => {
    if (token !== generation) return;
    if (typeof progress?.stalled === 'boolean') { activity.setStalled(progress.stalled); return; }
    if (progress?.failure) { failed = true; notice(progress.failure); render(); return; }
    if (text) { bootStatus = text; $('status').textContent = text; }
    if (progress) preparation = progress;
    renderWork();
  });
  engine = current;
  renderWork();
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
      for (const id of ['cols', 'rows']) {
        if (Number.isInteger(saved[id]) && saved[id] >= 2 && saved[id] <= 500) $(id).value = saved[id];
      }
      if (typeof saved.seed === 'string') $('seed').value = saved.seed.slice(0, 20);
      if (['informed', 'legacy'].includes(saved.aiStartPlacement)) $('ai-start-policy').value = saved.aiStartPlacement;
      if ($('ai-start-policy').value === 'legacy') document.querySelector('.advanced-setup').open = true;
    }
  } catch { /* Invalid or inaccessible settings are ignored. */ }
  $('track').disabled = false; $('start').disabled = false;
  drawRoster(); updateTrack();
  board.set(catalog.find(t => t.id === $('track').value) ?? {cols: 86, rows: 48});
  $('setup').showModal();
}
init().catch(error => { notice(error.message); $('setup-error').textContent = error.message; });
