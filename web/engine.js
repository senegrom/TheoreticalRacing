/** Own one isolated browser JVM. Destroying a race also stops its Java workers. */
export class Engine {
  constructor(onStatus = () => {}) {
    this.next = 1;
    this.pending = new Map();
    this.dead = false;
    this.frame = document.createElement('iframe');
    this.frame.hidden = true;
    this.frame.title = 'Java racing engine';
    this.frame.src = new URL('./runtime.html', import.meta.url).href;
    this.ready = new Promise((resolve, reject) => {
      this.resolveReady = resolve;
      this.rejectReady = reject;
    });
    this.ready.catch(() => {});
    this.listener = event => {
      if (event.origin !== location.origin || event.source !== this.frame.contentWindow) return;
      const message = event.data;
      if (!message || message.scope !== 'theoretical-racing') return;
      if (message.status) onStatus(message.status);
      if (message.ready) this.resolveReady();
      if (message.fatal) this.rejectReady(new Error(message.fatal));
      const request = this.pending.get(message.id);
      if (request) {
        clearTimeout(request.timer);
        this.pending.delete(message.id);
        if (message.error) request.reject(new Error(message.error));
        else request.resolve(message.result);
      }
    };
    window.addEventListener('message', this.listener);
    document.body.append(this.frame);
    this.bootTimer = setTimeout(() => this.rejectReady(new Error('The Java runtime did not load. Check your connection and retry.')), 180_000);
    this.ready.finally(() => clearTimeout(this.bootTimer)).catch(() => {});
  }
  async call(method, ...args) {
    await this.ready;
    if (this.dead) throw new DOMException('Race closed', 'AbortError');
    const id = this.next++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error('The Java engine did not respond. Start a new race to recover.'));
      }, 300_000);
      this.pending.set(id, {resolve, reject, timer});
      this.frame.contentWindow.postMessage({scope: 'theoretical-racing', id, method, args}, location.origin);
    });
  }
  destroy() {
    if (this.dead) return;
    this.dead = true;
    const error = new DOMException('Race closed', 'AbortError');
    this.rejectReady(error);
    clearTimeout(this.bootTimer);
    for (const request of this.pending.values()) {
      clearTimeout(request.timer);
      request.reject(error);
    }
    this.pending.clear();
    window.removeEventListener('message', this.listener);
    this.frame.remove();
  }
}
