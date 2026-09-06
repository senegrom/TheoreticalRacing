/** Accessible, honest work feedback. Percentages describe the current scan only. */
export class Activity {
  constructor(root) {
    this.root = root;
    this.label = root.querySelector('[data-work-label]');
    this.detail = root.querySelector('[data-work-detail]');
    this.elapsed = root.querySelector('[data-work-elapsed]');
    this.slow = root.querySelector('[data-work-slow]');
    this.bar = root.querySelector('progress');
    this.key = '';
    this.warning = root.querySelector('[data-work-stalled]');
    this.continueButton = root.querySelector('#keep-waiting');
  }
  show(key, label, progress = null) {
    if (this.key !== key) {
      this.key = key;
      this.started = performance.now();
      clearInterval(this.timer);
      this.timer = setInterval(() => this.clock(), 250);
    }
    this.root.hidden = false;
    this.label.textContent = label;
    const phase = (progress?.phase || 'Working in the background; the track view stays responsive.') +
      (Number.isInteger(progress?.pass) ? ` (stage ${progress.pass})` : '');
    const done = Number(progress?.done), total = Number(progress?.total);
    const measured = Number.isFinite(done) && Number.isFinite(total) && total > 0 && done >= 0;
    if (measured) {
      const value = Math.min(1, done / total);
      this.bar.value = value;
      this.detail.textContent = `${phase} · ${Math.floor(value * 100)}% of this ${progress.unit === 'resources' ? 'download' : 'scan'}`;
    } else {
      this.bar.removeAttribute('value');
      this.detail.textContent = phase + (done > 0 ? ` · ${Math.floor(done).toLocaleString()} ${progress?.unit || 'states explored'}` : '');
    }
    this.bar.setAttribute('aria-label', phase);
    this.clock();
  }
  setStalled(stalled) {
    this.warning.hidden = !stalled;
    this.continueButton.hidden = !stalled;
    this.root.dataset.stalled = String(stalled);
  }
  clock() {
    const seconds = Math.floor((performance.now() - this.started) / 1000);
    this.elapsed.textContent = seconds < 60 ? `${seconds}s elapsed` : `${Math.floor(seconds / 60)}m ${seconds % 60}s elapsed`;
    this.slow.hidden = seconds < 15;
  }
  hide() {
    this.setStalled(false);
    this.key = '';
    clearInterval(this.timer);
    this.root.hidden = true;
  }
}
