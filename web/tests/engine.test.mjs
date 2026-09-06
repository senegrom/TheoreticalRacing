/** Deterministic watchdog regressions: no sleeps, no Java/AI stand-ins. */
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Engine} from '../engine.js';

function harness(t) {
  const originals = {Worker: globalThis.Worker, setTimeout, clearTimeout};
  let time = 0, next = 1;
  const timers = new Map(), reports = [];
  globalThis.setTimeout = (fn, delay) => { const id = next++; timers.set(id, {fn, at: time + delay}); return id; };
  globalThis.clearTimeout = id => timers.delete(id);
  class Worker {
    constructor() { this.messages = []; this.terminated = false; }
    postMessage(message) { this.messages.push(message); }
    terminate() { this.terminated = true; }
    send(message) { this.onmessage({data: {scope: 'theoretical-racing', ...message}}); }
  }
  globalThis.Worker = Worker;
  const e = new Engine((s, p) => reports.push(p));
  t.after(() => { e.destroy(); Object.assign(globalThis, originals); });
  function tick(ms) {
    const target = time + ms;
    while (true) {
      const due = [...timers].filter(([, v]) => v.at <= target).sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      time = due[1].at; timers.delete(due[0]); due[1].fn();
    }
    time = target;
  }
  return {e, reports, tick, worker: e.worker, timers};
}

async function pending(e, method = 'tick') {
  const result = e.call(method);
  await Promise.resolve();
  return {result, id: e.next - 1};
}

test('boot silence warns, Keep waiting preserves startup, and late readiness succeeds', async t => {
  const {e, worker, tick} = harness(t);
  tick(180000); assert.equal(e.stalled, true); assert.equal(e.dead, false);
  e.keepWaiting(); assert.equal(e.stalled, false);
  tick(179999); assert.equal(e.dead, false); assert.equal(e.stalled, false);
  worker.send({ready: true}); await e.ready;
  tick(999999); assert.equal(e.dead, false); assert.equal(e.stalled, false);
});

test('real progress at 299999ms extends monitoring; the old deadline cannot kill work', async t => {
  const {e, worker, tick} = harness(t);
  worker.send({ready: true});
  const {result, id} = await pending(e);
  tick(299999);
  worker.send({progress: {phase: 'Mapping', done: 50, total: 100}});
  tick(1); assert.equal(e.dead, false); assert.equal(e.stalled, false);
  assert.equal(e.pending.size, 1);
  tick(299999); assert.equal(e.stalled, true); assert.equal(e.dead, false);
  worker.send({id, result: 'complete'});
  assert.equal(await result, 'complete'); assert.equal(e.stalled, false);
});

test('repeated progress is not advancement; silent AI may continue and finish', async t => {
  const {e, worker, tick} = harness(t);
  worker.send({ready: true});
  const {result, id} = await pending(e);
  worker.send({progress: {phase: 'Mapping', done: 50, total: 100}});
  tick(299999); worker.send({progress: {phase: 'Mapping', done: 50, total: 100}});
  tick(1); assert.equal(e.stalled, true); assert.equal(e.dead, false);
  e.keepWaiting(); tick(300000); assert.equal(e.stalled, true);
  tick(900000); assert.equal(e.pending.size, 1); assert.equal(worker.terminated, false);
  worker.send({id, result: 'finished later'}); assert.equal(await result, 'finished later');
});

test('progress automatically dismisses warning and Stop still rejects every pending call', async t => {
  const {e, worker, tick, timers} = harness(t);
  worker.send({ready: true});
  const a = await pending(e), b = await pending(e, 'snapshot');
  const rejects = [assert.rejects(a.result, {name: 'AbortError'}), assert.rejects(b.result, {name: 'AbortError'})];
  tick(300000); assert.equal(e.stalled, true);
  worker.send({progress: {phase: 'Mapping', done: 51, total: 100}});
  assert.equal(e.stalled, false);
  e.destroy(); await Promise.all(rejects);
  assert.equal(worker.terminated, true); assert.equal(e.pending.size, 0); assert.equal(timers.size, 0);
  worker.send({id: a.id, result: 'stale'}); assert.equal(e.dead, true);
});

test('readiness replies do not extend an unrelated silent AI call', async t => {
  const {e, worker, tick} = harness(t);
  worker.send({ready: true}); const a = await pending(e);
  tick(299999); const probe = await pending(e, 'readiness');
  worker.send({id: probe.id, result: {ready: false}}); await probe.result;
  tick(1); assert.equal(e.stalled, true); assert.equal(e.dead, false);
  const rejection = assert.rejects(a.result, {name: 'AbortError'}); e.destroy(); await rejection;
});

test('fatal worker errors still terminate and reject all queued requests', async t => {
  const {e, worker, timers} = harness(t);
  worker.send({ready: true}); const a = await pending(e), b = await pending(e, 'log');
  const errors = [assert.rejects(a.result, /broken/), assert.rejects(b.result, /broken/)];
  worker.send({fatal: 'broken'}); await Promise.all(errors);
  assert.equal(e.dead, true); assert.equal(worker.terminated, true); assert.equal(timers.size, 0);
});
