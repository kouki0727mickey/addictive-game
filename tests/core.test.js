const test = require('node:test');
const assert = require('node:assert');
const Core = require('../js/core.js');
const { play, playHuman } = require('./bot.js');

test('rng is deterministic', () => {
  const a = Core.mulberry32(42);
  const b = Core.mulberry32(42);
  for (let i = 0; i < 10; i++) assert.strictEqual(a(), b());
});

test('same seed produces same run', () => {
  const r1 = play(123, 30);
  const r2 = play(123, 30);
  assert.strictEqual(r1.score, r2.score);
  assert.strictEqual(r1.t, r2.t);
});

test('idle player eventually dies', () => {
  const s = Core.createGame(7);
  for (let i = 0; i < 60 * 60 && s.alive; i++) Core.step(s, 1 / 60);
  assert.strictEqual(s.alive, false);
});

test('first obstacle is not immediately on top of the player', () => {
  for (let seed = 1; seed < 200; seed++) {
    const s = Core.createGame(seed);
    for (let i = 0; i < 60; i++) Core.step(s, 1 / 60); // 1s idle
    assert.ok(s.alive, 'seed ' + seed + ' died within 1s of doing nothing');
  }
});

test('switchRing toggles and emits', () => {
  const s = Core.createGame(1);
  Core.switchRing(s);
  assert.strictEqual(s.ring, 0);
  const ev = Core.drainEvents(s);
  assert.strictEqual(ev[0].type, 'switch');
  for (let i = 0; i < 30; i++) Core.step(s, 1 / 60);
  assert.strictEqual(s.ringPos, 0);
});

test('autopilot survives long on most seeds (levels are fair)', () => {
  let survived = 0;
  const N = 100;
  const deaths = [];
  for (let seed = 1; seed <= N; seed++) {
    const s = play(seed, 90);
    if (s.alive) survived++;
    else deaths.push(seed + '@' + s.t.toFixed(1) + 's/score' + s.score);
  }
  assert.ok(survived >= N * 0.97, 'only ' + survived + '/' + N + ' survived: ' + deaths.slice(0, 10).join(', '));
});

test('big dt does not tunnel through spikes', () => {
  const s = Core.createGame(99);
  for (let i = 0; i < 400 && s.alive; i++) Core.step(s, 0.1);
  assert.strictEqual(s.alive, false);
});

test('a human-like player (200ms reaction, ±60ms jitter) survives the opening 30s', () => {
  let ok = 0;
  const N = 60;
  for (let seed = 1; seed <= N; seed++) if (playHuman(seed, 30, 0.2, 0.06).alive) ok++;
  assert.ok(ok >= N * 0.95, ok + '/' + N);
});

test('speed ramps with spikes passed, not with score', () => {
  const s = Core.createGame(5);
  s.score = 10000;
  Core.step(s, 1 / 60);
  assert.ok(Math.abs(s.speed - Core.CONFIG.baseSpeed) < 1e-9);
  s.passedSpikes = Core.CONFIG.rampSpikes;
  Core.step(s, 1 / 60);
  assert.ok(Math.abs(s.speed - Core.CONFIG.maxSpeed) < 1e-9);
});

test('no live object is ever more than the spawn horizon ahead (no lap overlap)', () => {
  const limit = Core.CONFIG.spawnAhead + 1e-6;
  for (let seed = 1; seed <= 20; seed++) {
    const s = Core.createGame(seed);
    s.passedSpikes = Core.CONFIG.rampSpikes; // late-game patterns
    for (let i = 0; i < 60 * 40 && s.alive; i++) {
      if (Core.autopilot(s)) Core.switchRing(s);
      Core.step(s, 1 / 60);
      for (const o of s.objects) assert.ok(o.angle - s.angle < limit, 'seed ' + seed + ': object ' + (o.angle - s.angle).toFixed(2) + ' rad ahead');
    }
  }
});

test('fever end grants a short invulnerability window', () => {
  const s = Core.createGame(3);
  s.fever = 0.001;
  Core.step(s, 1 / 60);
  assert.ok(s.grace > 0);
  // put a spike right on the player: must not kill during grace
  s.objects.push({ id: 999, type: 'spike', ring: s.ring, angle: s.angle, passed: false, dead: false });
  Core.step(s, 1 / 120);
  assert.ok(s.alive);
});
