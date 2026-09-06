/** One dedicated worker/JVM per race. Heavy Java never runs on the UI thread. */
export class Engine {
  constructor(onStatus = () => {}) {
    this.next = 1;
    this.pending = new Map();
    this.dead = false;
    this.onStatus = onStatus;
    this.ready = new Promise((resolve, reject) => {
      this.resolveReady = resolve;
      this.rejectReady = reject;
    });
    this.ready.catch(() => {});
    this.bootTimer = setTimeout(() => this.fail(new Error('The Java runtime did not load. Check your connection and start a new race.')), 180_000);
    try {
      // Classic workers support the runtime's documented importScripts loader.
      this.worker = new Worker(new URL('./runtime.js?v=3', import.meta.url), {name: 'racing-java'});
      this.worker.onmessage = ({data: message}) => {
        if (this.dead || !message || message.scope !== 'theoretical-racing') return;
        if (message.fatal) { this.fail(new Error(message.fatal)); return; }
        if (message.status || message.progress) this.onStatus(message.status, message.progress);
        if (message.ready) { clearTimeout(this.bootTimer); this.resolveReady(); }
        const request = this.pending.get(message.id);
        if (request) {
          clearTimeout(request.timer);
          this.pending.delete(message.id);
          if (message.error) request.reject(new Error(message.error));
          else request.resolve(message.result);
        }
      };
      this.worker.onerror = event => {
        event.preventDefault();
        this.fail(new Error(event.message || 'The Java worker stopped unexpectedly.'));
      };
      this.worker.onmessageerror = () => this.fail(new Error('The Java worker returned an unreadable response.'));
    } catch (error) { this.fail(error); }
  }
  async call(method, ...args) {
    await this.ready;
    if (this.dead) throw this.error ?? new DOMException('Race closed', 'AbortError');
    const id = this.next++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this.fail(new Error('The Java engine did not respond for five minutes. Start a new race to recover.')), 300_000);
      this.pending.set(id, {resolve, reject, timer});
      try { this.worker.postMessage({scope: 'theoretical-racing', id, method, args}); }
      catch (error) { this.fail(error); }
    });
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
