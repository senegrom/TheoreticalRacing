/** Canvas is a view only: all geometry, placements and move results come from Java. */
export class Board {
  constructor(canvas, onClick = null, onHover = () => {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.state = null;
    this.scale = 5;
    this.offset = [20, 20];
    this.fitMode = true;
    this.pointers = new Map();
    this.resize = new ResizeObserver(() => {
      const bounds = canvas.getBoundingClientRect();
      this.width = bounds.width;
      this.height = bounds.height;
      const dpr = Math.min(devicePixelRatio || 1, 3);
      canvas.width = Math.round(bounds.width * dpr);
      canvas.height = Math.round(bounds.height * dpr);
      this.dpr = dpr;
      if (this.fitMode) this.fit(); else this.draw();
    });
    this.resize.observe(canvas);
    if (!onClick) return;
    canvas.addEventListener('wheel', e => {
      e.preventDefault();
      const b = canvas.getBoundingClientRect();
      this.zoom(Math.exp(-Math.max(-300, Math.min(300, e.deltaY)) * .002), [e.clientX - b.left, e.clientY - b.top]);
    }, {passive: false});
    canvas.addEventListener('pointerdown', e => {
      if (e.button !== 0) return;
      canvas.setPointerCapture(e.pointerId);
      this.pointers.set(e.pointerId, [e.clientX, e.clientY]);
      this.gesture = {start: [e.clientX, e.clientY], moved: this.pointers.size > 1};
    });
    canvas.addEventListener('pointermove', e => {
      const b = canvas.getBoundingClientRect();
      onHover(this.world([e.clientX - b.left, e.clientY - b.top]));
      const old = this.pointers.get(e.pointerId);
      if (!old) return;
      const before = [...this.pointers.values()];
      this.pointers.set(e.pointerId, [e.clientX, e.clientY]);
      const after = [...this.pointers.values()];
      if (this.pointers.size > 1) {
        this.gesture.moved = true;
        const distance = a => Math.hypot(a[0][0] - a[1][0], a[0][1] - a[1][1]);
        const middle = a => [(a[0][0] + a[1][0]) / 2 - b.left, (a[0][1] + a[1][1]) / 2 - b.top];
        const m0 = middle(before), m1 = middle(after);
        this.zoom(distance(after) / Math.max(1, distance(before)), m0);
        this.offset[0] += m1[0] - m0[0]; this.offset[1] += m1[1] - m0[1];
      } else {
        if (Math.hypot(e.clientX - this.gesture.start[0], e.clientY - this.gesture.start[1]) > 4) this.gesture.moved = true;
        if (this.gesture.moved) {
          this.offset[0] += e.clientX - old[0]; this.offset[1] += e.clientY - old[1];
          this.fitMode = false;
        }
      }
      this.draw();
    });
    const finish = (e, cancelled) => {
      if (!this.pointers.has(e.pointerId)) return;
      this.pointers.delete(e.pointerId);
      if (!cancelled && !this.gesture.moved && !this.pointers.size) {
        const b = canvas.getBoundingClientRect();
        onClick(this.world([e.clientX - b.left, e.clientY - b.top]));
      }
      // A lifted pinch finger must never turn the remaining finger into a tap.
      this.gesture.moved = true;
    };
    canvas.addEventListener('pointerup', e => finish(e, false));
    canvas.addEventListener('pointercancel', e => finish(e, true));
  }
  world([x, y]) { return [(x - this.offset[0]) / this.scale, (y - this.offset[1]) / this.scale]; }
  screen([x, y]) { return [x * this.scale + this.offset[0], y * this.scale + this.offset[1]]; }
  set(state) { this.state = state; if (this.fitMode) this.fit(); else this.draw(); }
  fit() {
    if (!this.state || !this.width || !this.height) return;
    this.fitMode = true;
    const {cols = 86, rows = 48} = this.state;
    this.scale = Math.max(.1, Math.min((this.width - 40) / (cols + 1), (this.height - 40) / (rows + 1)));
    this.offset = [(this.width - cols * this.scale) / 2, (this.height - rows * this.scale) / 2];
    this.draw();
  }
  zoom(factor, anchor = [this.width / 2, this.height / 2]) {
    if (!Number.isFinite(factor)) return;
    const world = this.world(anchor);
    this.scale = Math.max(.1, Math.min(80, this.scale * factor));
    this.offset = [anchor[0] - world[0] * this.scale, anchor[1] - world[1] * this.scale];
    this.fitMode = false;
    this.draw();
  }
  focus() {
    const s = this.state;
    if (!s) return;
    let p = s.players?.[s.current]?.position;
    if (!p || p[0] < -1000) {
      if (s.left?.length && s.right?.length) p = [(s.left[0][0] + s.right[0][0]) / 2, (s.left[0][1] + s.right[0][1]) / 2];
      else { this.fit(); return; }
    }
    const v = s.players?.[s.current]?.velocity ?? [0, 0];
    this.scale = Math.min(25, Math.max(5, Math.min(this.width / (Math.abs(v[0]) * 2 + 14), this.height / (Math.abs(v[1]) * 2 + 14))));
    this.offset = [this.width / 2 - (p[0] + v[0] / 2) * this.scale, this.height / 2 - (p[1] + v[1] / 2) * this.scale];
    this.fitMode = false;
    this.draw();
  }
  draw() {
    const c = this.ctx, s = this.state;
    if (!c || !this.width || !this.height) return;
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    c.fillStyle = '#fdfbf5'; c.fillRect(0, 0, this.width, this.height);
    if (!s) return;
    const point = p => this.screen(p);
    const path = points => {
      c.beginPath();
      for (let i = 0; i < points.length; i++) { const p = point(points[i]); if (i) c.lineTo(...p); else c.moveTo(...p); }
    };
    const line = (points, color, width = 2) => { if (!points?.length) return; path(points); c.strokeStyle = color; c.lineWidth = width; c.stroke(); };
    const fill = (points, color) => { if (!points?.length) return; path(points); c.closePath(); c.fillStyle = color; c.fill(); };
    if (s.shape?.length) {
      c.beginPath();
      for (const [kind, x, y] of s.shape) {
        if (kind === 4) c.closePath();
        else if (kind === 0) c.moveTo(...point([x, y]));
        else c.lineTo(...point([x, y]));
      }
      c.fillStyle = '#e9ede2'; c.fill('nonzero');
    } else if (s.left?.length && s.right?.length) fill([...s.left, ...s.right.toReversed()], '#e9ede2');
    if (s.startZone) fill(s.startZone[0].map((x, i) => [x, s.startZone[1][i]]), '#b6d6bb');
    const first = this.world([0, 0]), last = this.world([this.width, this.height]);
    // Avoid spending time on invisible grid points on very large circuits.
    if (this.scale >= 5) {
      c.fillStyle = '#778a722f';
      for (let x = Math.max(0, Math.ceil(first[0])); x <= Math.min(s.cols, last[0]); x++) {
        for (let y = Math.max(0, Math.ceil(first[1])); y <= Math.min(s.rows, last[1]); y++) { const p = point([x, y]); c.fillRect(p[0] - .7, p[1] - .7, 1.4, 1.4); }
      }
    }
    line(s.left, '#2c5264', 2.2); line(s.right, '#2c5264', 2.2);
    if (s.left?.length && s.right?.length) line([s.left[0], s.right[0]], '#4b9671', 3);
    if (s.finish) line(s.finish, '#ae3928', 3);
    else if (s.left?.length && s.right?.length) line([s.left.at(-1), s.right.at(-1)], '#ae3928', 3);
    for (const seg of s.closures ?? []) line([[seg[0], seg[1]], [seg[2], seg[3]]], '#2c5264', 2.2);
    c.setLineDash([7, 5]);
    for (const seg of s.checkpoints ?? []) line([[seg[0], seg[1]], [seg[2], seg[3]]], '#b9850d');
    c.setLineDash([]);
    for (const start of s.starts ?? []) {
      const p = point(start); c.beginPath(); c.arc(...p, Math.max(2, Math.min(5, this.scale / 4)), 0, 2 * Math.PI); c.fillStyle = '#4b9671'; c.fill();
    }
    for (const player of s.players ?? []) {
      c.globalAlpha = .6;
      line(player.history?.slice(player.traceStart ?? 0), player.color, 2);
      c.globalAlpha = 1;
    }
    const current = s.players?.[s.current];
    if (s.prePath?.length && current) {
      c.setLineDash([5, 5]); line([current.position, ...s.prePath], '#60736a', 2); c.setLineDash([]);
    }
    for (const m of s.moves ?? []) {
      const p = point(m.position), r = Math.max(4, Math.min(10, this.scale * .3));
      c.strokeStyle = m.legal ? '#437960' : '#ae3928'; c.lineWidth = m.index === s.selected ? 3 : 1.5;
      if (m.index === s.selected) {
        c.beginPath(); c.arc(...p, r + 4, 0, Math.PI * 2); c.fillStyle = '#d8a12a70'; c.fill();
      }
      c.beginPath();
      if (m.legal) c.arc(...p, r, 0, Math.PI * 2);
      else { c.moveTo(p[0] - r, p[1] - r); c.lineTo(p[0] + r, p[1] + r); c.moveTo(p[0] + r, p[1] - r); c.lineTo(p[0] - r, p[1] + r); }
      c.stroke();
    }
    for (const [i, player] of (s.players ?? []).entries()) {
      if (player.position[0] < -1000) continue;
      const p = point(player.position);
      const r = 7;
      if (s.phase === 'PLAY' && i === s.current) {
        c.beginPath(); c.arc(...p, r + 4, 0, Math.PI * 2); c.strokeStyle = '#d8a12a'; c.lineWidth = 3; c.stroke();
      }
      c.beginPath(); c.arc(...p, r, 0, Math.PI * 2); c.fillStyle = player.color; c.fill(); c.strokeStyle = '#fff'; c.lineWidth = 2; c.stroke();
      c.font = 'bold 10px system-ui'; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.strokeStyle = '#000'; c.lineWidth = 2.5; c.strokeText(String(i + 1), p[0], p[1]); c.fillStyle = '#fff'; c.fillText(String(i + 1), p[0], p[1]);
      if (player.place < 0) { c.strokeStyle = '#ae3928'; c.lineWidth = 2; c.beginPath(); c.moveTo(p[0] - 10, p[1] - 10); c.lineTo(p[0] + 10, p[1] + 10); c.stroke(); }
    }
  }
}
