/** One worker/JVM per race. Watchdogs warn about silence, never discard a race. */
export class Engine {
  constructor(onStatus = () => {}) {
    this.next = 1;
    this.pending = new Map();
    this.snapshotState = null;
    this.dead = false;
    this.booting = true;
    this.stalled = false;
    this.lastStatus = '';
    this.lastProgress = '';
    this.onStatus = onStatus;
    this.ready = new Promise((resolve, reject) => {
      this.resolveReady = resolve;
      this.rejectReady = reject;
    });
    this.ready.catch(() => {});
    this.armBoot();
    try {
      this.worker = new Worker(new URL('./runtime.js?v=6', import.meta.url), {name: 'racing-java'});
      this.worker.onmessage = ({data: message}) => {
        if (this.dead || !message || message.scope !== 'theoretical-racing') return;
        if (message.fatal) { this.fail(new Error(message.fatal)); return; }
        // Repeated counters/heartbeats are not evidence that a search advanced.
        const signature = message.progress && JSON.stringify([
          message.progress.kind, message.progress.phase, message.progress.pass,
          message.progress.done, message.progress.total, message.progress.stage,
          message.progress.stages, message.progress.complete
        ]);
        const changedStatus = typeof message.status === 'string' && message.status && message.status !== this.lastStatus;
        const changedProgress = signature && signature !== this.lastProgress;
        if (changedStatus) this.lastStatus = message.status;
        if (changedProgress) this.lastProgress = signature;
        if (changedStatus || changedProgress) this.noteActivity();
        if (message.status || message.progress) this.onStatus(message.status, message.progress);
        if (message.ready) {
          this.booting = false;
          clearTimeout(this.bootTimer);
          this.setStalled(false);
          this.resolveReady();
        }
        const request = this.pending.get(message.id);
        if (request) {
          clearTimeout(request.timer);
          this.pending.delete(message.id);
          // Small readiness polls must not keep a silent long-running call alive.
          if (request.method !== 'readiness') this.noteActivity();
          if (!this.booting && this.pending.size === 0) this.setStalled(false);
          if (message.error) request.reject(new Error(message.error));
          else {
            try { request.resolve(this.mergeSnapshot(message.result)); }
            catch (error) { request.reject(error); }
          }
        }
      };
      this.worker.onerror = event => {
        event.preventDefault();
        this.fail(new Error(event.message || 'The Java worker stopped unexpectedly.'));
      };
      this.worker.onmessageerror = () => this.fail(new Error('The Java worker returned an unreadable response.'));
    } catch (error) { this.fail(error); }
  }
  armBoot() {
    clearTimeout(this.bootTimer);
    if (this.booting && !this.dead) this.bootTimer = setTimeout(() => this.setStalled(true), 180_000);
  }
  armRequest(request) {
    clearTimeout(request.timer);
    request.timer = setTimeout(() => this.setStalled(true), 300_000);
  }
  setStalled(value) {
    if (this.dead || this.stalled === value) return;
    this.stalled = value;
    this.onStatus('', {stalled: value});
  }
  noteActivity() {
    if (this.dead) return;
    this.setStalled(false);
    this.armBoot();
    for (const request of this.pending.values()) this.armRequest(request);
  }
  keepWaiting() {
    // User consent extends monitoring, not a search budget or the game rules.
    this.noteActivity();
  }
  async call(method, ...args) {
    await this.ready;
    if (this.dead) throw this.error ?? new DOMException('Race closed', 'AbortError');
    const id = this.next++;
    return new Promise((resolve, reject) => {
      const request = {resolve, reject, method};
      this.pending.set(id, request);
      this.armRequest(request);
      try { this.worker.postMessage({scope: 'theoretical-racing', id, method, args}); }
      catch (error) { this.fail(error); }
    });
  }
  mergeSnapshot(result) {
    if (!result || typeof result !== 'object' || !result._snapshot) return result;
    if (result._snapshot === 'full') {
      const next = {...result, __revision: result._revision};
      delete next._snapshot; delete next._revision;
      this.snapshotState = next;
      return next;
    }
    if (result._snapshot !== 'delta' || !this.snapshotState || result._base !== this.snapshotState.__revision)
      throw new Error('The Java state stream lost synchronization. Start a new race to recover.');
    const next = {...this.snapshotState, ...(result.set || {}), __revision: result._revision};
    if (result.geometry) Object.assign(next, result.geometry);
    if (result.players) {
      next.players = this.snapshotState.players.slice();
      for (const patch of result.players) {
        const old = this.snapshotState.players[patch.index];
        if (!old) throw new Error('Invalid player state delta');
        const player = {...old, ...(patch.set || {})};
        if (patch.history) player.history = patch.history;
        else if (patch.historyAppend) player.history = [...old.history, ...patch.historyAppend];
        next.players[patch.index] = player;
      }
    }
    this.snapshotState = next;
    return next;
  }
  fail(error) {
    if (this.dead) return;
    this.error = error;
    this.close(error);
    this.onStatus('', {failure: error.message});
  }
  close(error) {
    this.dead = true;
    this.rejectReady(error);
    clearTimeout(this.bootTimer);
    for (const request of this.pending.values()) {
      clearTimeout(request.timer);
      request.reject(error);
    }
    this.pending.clear();
    this.worker?.terminate();
  }
  destroy() {
    if (!this.dead) this.close(new DOMException('Race closed', 'AbortError'));
  }
}
