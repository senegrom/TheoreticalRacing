/** Stable activity slot with separate dependency-stage and current-work progress. */
const PREPARATION_STAGES = [
  ['Runtime', 'Load and start Java in the background worker'],
  ['Geometry', 'Validate the corridor, start zone and finish/checkpoint geometry'],
  ['Distances', 'One distance map for the whole field'],
  ['Cache', 'Check saved geometry-keyed maps; validated hits skip recomputation'],
  ['Finish routes', 'Exact finish reachability over positions and velocities'],
  ['Driving maps', 'Safe successors, manoeuvring, braking and speed certificates'],
  ['Lap routes', 'Checkpoint routes, repeated until their cycle converges'],
  ['Lap safety', 'Checkpoint safety, repeated until its cycle converges'],
  ['Lap driving', 'Driving maps for the different coherent multi-lap state set'],
];
export class Activity {
  constructor(root) {
    this.root = root;
    this.label = root.querySelector('[data-work-label]');
    this.detail = root.querySelector('[data-work-detail]');
    this.elapsed = root.querySelector('[data-work-elapsed]');
    this.slow = root.querySelector('[data-work-slow]');
    this.bar = root.querySelector('[data-work-progress]');
    this.warning = root.querySelector('[data-work-stalled]');
    this.continueButton = root.querySelector('#keep-waiting');
    this.preparation = root.querySelector('[data-preparation]');
    this.stageBar = root.querySelector('[data-preparation-progress]');
    this.stageSummary = root.querySelector('[data-preparation-summary]');
    this.stageList = root.querySelector('[data-preparation-stages]');
    this.key = ''; this.stage = 0; this.stages = 6; this.cached = false;
  }
  setPreparation(visible, progress = null, ready = false) {
    this.preparation.hidden = !visible;
    if (!visible) return;
    if ([6, 9].includes(progress?.stages)) this.stages = progress.stages;
    if (Number.isInteger(progress?.stage)) this.stage = Math.max(this.stage, Math.min(this.stages, progress.stage));
    if (ready || progress?.complete) this.stage = this.stages;
    this.cached ||= Boolean(progress?.cached);
    this.stageBar.max = this.stages;
    this.stageBar.value = this.stage;
    this.stageBar.setAttribute('aria-label', `Preparation: ${this.stage} of ${this.stages} stages satisfied; not a time estimate`);
    this.stageSummary.textContent = this.stage === this.stages ? 'All preparation stages ready' : `${this.stage} / ${this.stages} stages complete`;
    if (this.stageList.children.length !== this.stages) {
      this.stageList.replaceChildren(...PREPARATION_STAGES.slice(0, this.stages).map(([name, description]) => {
        const item = document.createElement('li'); item.textContent = name; item.title = description; return item;
      }));
    }
    for (const [i, item] of [...this.stageList.children].entries()) {
      const status = i < this.stage ? 'complete' : i === this.stage ? 'current' : 'pending';
      item.dataset.state = status;
      item.setAttribute('aria-label', `${PREPARATION_STAGES[i][0]}: ${status}${this.cached && i >= 4 && i <= 5 && status === 'complete' ? ' (saved maps reused where available)' : ''}`);
    }
  }
  show(key, label, progress = null) {
    if (this.key !== key || !this.active) {
      this.key = key;
      this.started = performance.now();
      clearInterval(this.timer);
      this.timer = setInterval(() => this.clock(), 250);
    }
    this.active = true;
    this.root.hidden = false;
    this.root.dataset.active = 'true';
    this.label.textContent = label;
    this.label.title = label;
    const phase = (progress?.phase || 'Working in the background; the track view stays responsive.') +
      (Number.isInteger(progress?.pass) ? ` · pass ${progress.pass}` : '');
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
    this.detail.title = this.detail.textContent;
    this.bar.setAttribute('aria-label', phase);
    this.clock();
  }
  /** Keep the slot and controls mounted between operations: no display toggling. */
  idle(label, detail = '') {
    this.active = false; this.key = ''; clearInterval(this.timer);
    this.root.hidden = false; this.root.dataset.active = 'false';
    this.label.textContent = label; this.label.title = label;
    this.detail.textContent = detail; this.detail.title = detail;
    this.elapsed.textContent = 'Ready';
    this.bar.value = 1; this.bar.setAttribute('aria-label', 'No calculation pending');
    this.slow.hidden = true;
    this.setStalled(false);
  }
  setStalled(stalled) {
    this.stalled = stalled;
    this.warning.hidden = !stalled;
    this.continueButton.hidden = !stalled;
    this.root.dataset.stalled = String(stalled);
    if (this.active) this.clock();
  }
  clock() {
    const seconds = Math.floor((performance.now() - this.started) / 1000);
    this.elapsed.textContent = seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    this.elapsed.title = `${seconds} seconds elapsed`;
    this.slow.hidden = seconds < 15 || this.stalled;
  }
  hide() {
    this.active = false; this.setStalled(false);
    this.key = ''; this.stage = 0; this.stages = 6; this.cached = false;
    clearInterval(this.timer);
    this.root.hidden = true;
  }
}
