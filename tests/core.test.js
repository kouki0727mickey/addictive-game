const test = require('node:test');
const assert = require('node:assert');
const Core = require('../js/core.js');
const { play } = require('./bot.js');

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
