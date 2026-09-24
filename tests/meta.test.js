const test = require('node:test');
const assert = require('node:assert');
const Meta = require('../js/meta.js');

function memStorage() {
  const m = {};
  return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => (m[k] = String(v)) };
}
const rng = () => 0.3;

test('load gives defaults with three distinct missions', () => {
  const s = Meta.load(memStorage(), rng);
  assert.strictEqual(s.best, 0);
  assert.strictEqual(s.missions.length, 3);
  assert.strictEqual(new Set(s.missions.map((m) => m.kind)).size, 3);
});

test('corrupt storage falls back to defaults', () => {
  const st = memStorage();
  st.setItem(Meta.KEY, '{not json');
  const s = Meta.load(st, rng);
  assert.strictEqual(s.coins, 0);
});

test('persist + load round trip', () => {
  const st = memStorage();
  const s = Meta.load(st, rng);
  s.coins = 77;
  Meta.persist(st, s);
  assert.strictEqual(Meta.load(st, rng).coins, 77);
});

test('applyRun updates best and coins', () => {
  const s = Meta.load(memStorage(), rng);
  const r = Meta.applyRun(s, { score: 40, gems: 5, nearMisses: 0, bestCombo: 3, feverCount: 0 }, rng);
  assert.strictEqual(s.best, 40);
  assert.ok(r.coins >= 10);
  assert.strictEqual(r.newBest, false); // first run is not celebrated as "new best"
  const r2 = Meta.applyRun(s, { score: 41, gems: 0, nearMisses: 0, bestCombo: 0, feverCount: 0 }, rng);
  assert.strictEqual(r2.newBest, true);
});

test('levels', () => {
  assert.strictEqual(Meta.levelFromXp(0), 1);
  assert.strictEqual(Meta.levelFromXp(Meta.xpForLevel(1) - 1), 1);
  assert.strictEqual(Meta.levelFromXp(Meta.xpForLevel(1)), 2);
  assert.strictEqual(Meta.levelFromXp(Meta.xpForLevel(2)), 3);
  const p = Meta.levelProgress(Meta.xpForLevel(1) + 5);
  assert.deepStrictEqual(p, { level: 2, into: 5, need: Meta.xpForLevel(2) - Meta.xpForLevel(1) });
  assert.deepStrictEqual(Meta.levelProgress(0), { level: 1, into: 0, need: Meta.xpForLevel(1) });
});

test('daily streak', () => {
  const s = Meta.defaultSave();
  const day = 24 * 3600 * 1000;
  const t0 = new Date(2026, 0, 1, 12).getTime();
  assert.strictEqual(Meta.checkDaily(s, t0), 10);
  assert.strictEqual(Meta.checkDaily(s, t0 + 1000), 0);
  assert.strictEqual(Meta.checkDaily(s, t0 + day), 15);
  assert.strictEqual(s.streak, 2);
  assert.strictEqual(Meta.checkDaily(s, t0 + 3 * day), 10);
  assert.strictEqual(s.streak, 1);
});

test('buy skin', () => {
  const s = Meta.defaultSave();
  assert.strictEqual(Meta.buySkin(s, 'sakura'), false);
  s.coins = 100;
  assert.strictEqual(Meta.buySkin(s, 'sakura'), true);
  assert.strictEqual(s.coins, 20);
  assert.strictEqual(s.skin, 'sakura');
  assert.strictEqual(Meta.buySkin(s, 'neon'), true);
  assert.strictEqual(s.coins, 20);
});

test('missions complete and refill', () => {
  const s = Meta.load(memStorage(), rng);
  const before = s.missions.map((m) => m.kind);
  const run = { score: 1000, gems: 100, nearMisses: 100, bestCombo: 100, feverCount: 10 };
  const r = Meta.applyRun(s, run, rng);
  assert.ok(r.completed.length >= 1);
  assert.strictEqual(s.missions.length, 3);
  assert.ok(before.length === 3);
});

test('sanitize repairs hostile / broken saves', () => {
  const s = Meta.sanitize({ coins: 'lots', best: -5, xp: NaN, owned: 'neon', skin: 'hacker', missions: [{ kind: 'score', goal: 20, progress: 3, text: '<img src=x onerror=alert(1)>' }, { kind: 'nope', goal: 1 }] });
  assert.strictEqual(s.coins, 0);
  assert.strictEqual(s.best, 0);
  assert.strictEqual(s.xp, 0);
  assert.deepStrictEqual(s.owned, ['neon']);
  assert.strictEqual(s.skin, 'neon');
  assert.strictEqual(s.missions.length, 1);
  assert.ok(!('text' in s.missions[0])); // texts come from i18n, never from the save
  assert.deepStrictEqual(Meta.sanitize(null), Meta.defaultSave());
  assert.deepStrictEqual(Meta.sanitize(42), Meta.defaultSave());
});

test('load tolerates a storage that throws', () => {
  const bad = { getItem() { throw new Error('SecurityError'); }, setItem() { throw new Error('QuotaExceeded'); } };
  const s = Meta.load(bad, rng);
  assert.strictEqual(s.missions.length, 3);
  Meta.persist(bad, s); // must not throw
});

test('economy: a beginner (~20 pts/run) unlocks the first skin in 3-8 runs', () => {
  const s = Meta.load(memStorage(), rng);
  const first = Meta.SKINS.filter((k) => k.price > 0).sort((a, b) => a.price - b.price)[0];
  let runs = 0;
  while (s.coins < first.price && runs < 50) {
    Meta.applyRun(s, { score: 20, gems: 3, nearMisses: 1, bestCombo: 2, feverCount: 0 }, rng);
    runs++;
  }
  assert.ok(runs >= 3 && runs <= 8, 'first skin after ' + runs + ' runs');
});

test('economy: one monster run cannot buy out the shop', () => {
  const s = Meta.load(memStorage(), rng);
  const r = Meta.applyRun(s, { score: 5000, gems: 300, nearMisses: 80, bestCombo: 100, feverCount: 10 }, rng);
  const total = Meta.SKINS.reduce((a, k) => a + k.price, 0);
  assert.ok(r.coins < total * 0.2, 'monster run paid ' + r.coins + ' of ' + total);
});

test('coins grow with score but with diminishing returns', () => {
  const c = (score) => Meta.runCoins({ score, gems: 0 });
  assert.ok(c(100) > c(10));
  assert.ok(c(1000) - c(900) < c(100) - c(0));
});

test('daily challenge: same seed per day, separate best, resets next day', () => {
  assert.strictEqual(Meta.dailySeed('2026-9-24'), Meta.dailySeed('2026-9-24'));
  assert.notStrictEqual(Meta.dailySeed('2026-9-24'), Meta.dailySeed('2026-9-25'));
  const s = Meta.defaultSave();
  let r = Meta.recordDaily(s, '2026-9-24', 30);
  assert.deepStrictEqual(r, { prevBest: 0, best: 30, newBest: false });
  r = Meta.recordDaily(s, '2026-9-24', 45);
  assert.deepStrictEqual(r, { prevBest: 30, best: 45, newBest: true });
  assert.strictEqual(s.daily.tries, 2);
  assert.strictEqual(Meta.dailyBest(s, '2026-9-25'), 0);
  Meta.recordDaily(s, '2026-9-25', 10);
  assert.deepStrictEqual(s.daily, { day: '2026-9-25', best: 10, tries: 1 });
  assert.deepStrictEqual(Meta.sanitize({ daily: { day: 5 } }).daily, null);
});

test('language setting is sanitized', () => {
  assert.strictEqual(Meta.sanitize({ lang: 'en' }).lang, 'en');
  assert.strictEqual(Meta.sanitize({ lang: 'ja' }).lang, 'ja');
  assert.strictEqual(Meta.sanitize({ lang: '<script>' }).lang, 'auto');
  assert.strictEqual(Meta.defaultSave().lang, 'auto');
});
