/* ORBIT SWITCH — tiny WebAudio synth, no assets. */
(function (root) {
  'use strict';

  let ctx = null;
  let master = null;
  let muted = false;

  function ensure() {
    if (ctx) return ctx;
    const AC = root.AudioContext || root.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.35;
    master.connect(ctx.destination);
    return ctx;
  }

  function tone(freq, dur, type, vol, slide) {
    if (muted) return;
    const c = ensure();
    if (!c) return;
    const t = c.currentTime;
    const o = c.createOscillator();
    const g = c.createGain();
    o.type = type || 'sine';
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(slide, t + dur);
    g.gain.setValueAtTime(vol || 0.3, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g);
    g.connect(master);
    o.start(t);
    o.stop(t + dur + 0.02);
  }

  const SCALE = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24];

  const Sfx = {
    unlock() {
      const c = ensure();
      if (c && c.state === 'suspended') c.resume();
    },
    setMuted(m) {
      muted = m;
    },
    isMuted() {
      return muted;
    },
    switch() {
      tone(520, 0.05, 'triangle', 0.12, 700);
    },
    gem(combo) {
      const n = SCALE[Math.min(combo - 1, SCALE.length - 1)] || 0;
      tone(660 * Math.pow(2, n / 12), 0.12, 'sine', 0.25);
    },
    nearMiss() {
      tone(1200, 0.08, 'square', 0.08, 1800);
    },
    smash() {
      tone(180, 0.15, 'sawtooth', 0.18, 60);
    },
    fever() {
      [0, 4, 7, 12].forEach((n, i) => setTimeout(() => tone(523 * Math.pow(2, n / 12), 0.12, 'square', 0.12), i * 60));
    },
    death() {
      tone(300, 0.5, 'sawtooth', 0.25, 40);
    },
    best() {
      [0, 4, 7, 12, 16].forEach((n, i) => setTimeout(() => tone(523 * Math.pow(2, n / 12), 0.18, 'triangle', 0.18), i * 90));
    },
    coin() {
      tone(988, 0.06, 'square', 0.08);
      setTimeout(() => tone(1319, 0.1, 'square', 0.08), 60);
    },
  };

  root.Sfx = Sfx;
})(typeof self !== 'undefined' ? self : this);
