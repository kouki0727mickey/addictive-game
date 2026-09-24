/*
 * ORBIT SWITCH — meta progression: coins, skins, missions, level, daily streak.
 * Storage is injected so the module can be tested in Node.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.OrbitMeta = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const KEY = 'orbit-switch-save-v1';

  // Display names and mission texts live in js/i18n.js ('skin.<id>', 'mission.<kind>'), so saves stay language-neutral.
  const SKINS = [
    { id: 'neon', price: 0, color: '#4df3ff', trail: '#4df3ff' },
    { id: 'sakura', price: 80, color: '#ff7ad9', trail: '#ffb3ec' },
    { id: 'lime', price: 200, color: '#b6ff4d', trail: '#e2ff9e' },
    { id: 'sun', price: 400, color: '#ffc94d', trail: '#ff7b3a' },
    { id: 'void', price: 700, color: '#b28cff', trail: '#6a3dff' },
    { id: 'ghost', price: 1100, color: '#eef2ff', trail: '#8a90b8' },
    { id: 'rainbow', price: 1600, color: 'rainbow', trail: 'rainbow' },
  ];

  const MISSION_POOL = [
    { kind: 'score', goals: [20, 40, 70, 100, 150] },
    { kind: 'gems', goals: [5, 10, 20, 35] },
    { kind: 'nearMisses', goals: [2, 4, 8] },
    { kind: 'bestCombo', goals: [5, 10, 20] },
    { kind: 'feverCount', goals: [1, 2, 3] },
    { kind: 'plays', goals: [3, 5, 10], cumulative: true },
  ];

  function today(now) {
    const d = new Date(now);
    return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
  }

  function dayDiff(a, b) {
    const pa = a.split('-').map(Number);
    const pb = b.split('-').map(Number);
    const ta = Date.UTC(pa[0], pa[1] - 1, pa[2]);
    const tb = Date.UTC(pb[0], pb[1] - 1, pb[2]);
    return Math.round((tb - ta) / 86400000);
  }

  function defaultSave() {
    return {
      best: 0,
      coins: 0,
      xp: 0,
      plays: 0,
      totalGems: 0,
      skin: 'neon',
      owned: ['neon'],
      missions: [],
      missionTier: 0,
      lastDay: null,
      streak: 0,
      muted: false,
      lang: 'auto', // 'auto' follows the device language; 'ja' / 'en' are explicit choices
      daily: null, // { day, best, tries } for today's challenge stage
    };
  }

  function makeMission(save, rng, excludeKinds) {
    const pool = MISSION_POOL.filter((m) => excludeKinds.indexOf(m.kind) === -1);
    const m = pool[Math.floor(rng() * pool.length)];
    const tier = Math.min(m.goals.length - 1, Math.floor(save.missionTier / 2));
    const goal = m.goals[tier];
    return { kind: m.kind, goal, progress: 0, reward: 10 + tier * 10, cumulative: !!m.cumulative };
  }

  function fillMissions(save, rng) {
    while (save.missions.length < 3) {
      save.missions.push(makeMission(save, rng, save.missions.map((m) => m.kind)));
    }
  }

  function num(v, fallback) {
    return typeof v === 'number' && isFinite(v) && v >= 0 ? v : fallback;
  }

  // Repair anything a stale, hand-edited or corrupt save could contain.
  function sanitize(raw) {
    const d = defaultSave();
    if (!raw || typeof raw !== 'object') return d;
    for (const k of ['best', 'coins', 'xp', 'plays', 'totalGems', 'missionTier', 'streak']) d[k] = Math.floor(num(raw[k], d[k]));
    d.muted = raw.muted === true;
    d.lang = raw.lang === 'ja' || raw.lang === 'en' ? raw.lang : 'auto';
    d.lastDay = typeof raw.lastDay === 'string' ? raw.lastDay : null;
    if (raw.daily && typeof raw.daily.day === 'string') {
      d.daily = { day: raw.daily.day, best: Math.floor(num(raw.daily.best, 0)), tries: Math.floor(num(raw.daily.tries, 0)) };
    }
    if (Array.isArray(raw.owned)) {
      d.owned = raw.owned.filter((id) => SKINS.some((s) => s.id === id));
      if (d.owned.indexOf('neon') === -1) d.owned.unshift('neon');
    }
    d.skin = d.owned.indexOf(raw.skin) !== -1 ? raw.skin : 'neon';
    if (Array.isArray(raw.missions)) {
      d.missions = raw.missions
        .filter((m) => m && MISSION_POOL.some((p) => p.kind === m.kind) && num(m.goal, 0) > 0)
        .slice(0, 3)
        .map((m) => {
          const def = MISSION_POOL.find((p) => p.kind === m.kind);
          return { kind: m.kind, goal: m.goal, progress: num(m.progress, 0), reward: num(m.reward, 15), cumulative: !!def.cumulative };
        });
    }
    return d;
  }

  function load(storage, rng) {
    let raw = null;
    try {
      const str = storage && storage.getItem(KEY);
      if (str) raw = JSON.parse(str);
    } catch (e) {
      /* corrupt or unavailable storage: start fresh */
    }
    const save = sanitize(raw);
    fillMissions(save, rng || Math.random);
    return save;
  }

  function persist(storage, save) {
    try {
      if (storage) storage.setItem(KEY, JSON.stringify(save));
    } catch (e) {
      /* storage full or blocked: ignore */
    }
  }

  // Cumulative xp needed to reach level n+1 from level 1. Quadratic-ish so early levels come fast.
  function xpForLevel(n) {
    return 40 * n * n + 10 * n;
  }

  function levelFromXp(xp) {
    let lvl = 1;
    while (xp >= xpForLevel(lvl)) lvl++;
    return lvl;
  }

  function levelProgress(xp) {
    const lvl = levelFromXp(xp);
    const prev = lvl === 1 ? 0 : xpForLevel(lvl - 1);
    const next = xpForLevel(lvl);
    return { level: lvl, into: xp - prev, need: next - prev };
  }

  // Called once when the player opens the game. Returns daily bonus coins (0 if already claimed).
  function checkDaily(save, now) {
    const t = today(now);
    if (save.lastDay === t) return 0;
    const diff = save.lastDay ? dayDiff(save.lastDay, t) : 999;
    save.streak = diff === 1 ? save.streak + 1 : 1;
    save.lastDay = t;
    const bonus = Math.min(10 + (save.streak - 1) * 5, 50);
    save.coins += bonus;
    return bonus;
  }

  // Coins grow with the square root of score: good runs pay more, but a single great run
  // can't unlock the whole shop (score itself grows super-linearly through multipliers).
  function runCoins(run) {
    return 2 + Math.floor(Math.sqrt(Math.max(0, run.score)) * 1.2) + Math.floor(Math.sqrt(Math.max(0, run.gems)) * 2);
  }

  // Apply the result of a run. Returns a summary for the game-over screen.
  function applyRun(save, run, rng) {
    const summary = { newBest: false, coins: 0, levelUps: 0, completed: [], prevBest: save.best };
    save.plays++;
    save.totalGems += run.gems;
    if (run.score > save.best) {
      save.best = run.score;
      summary.newBest = summary.prevBest > 0;
    }
    summary.coins += runCoins(run);

    const lvlBefore = levelFromXp(save.xp);
    save.xp += run.score;
    const lvlAfter = levelFromXp(save.xp);
    summary.levelUps = lvlAfter - lvlBefore;
    summary.coins += summary.levelUps * 10;

    for (const m of save.missions) {
      const value = m.kind === 'plays' ? 1 : run[m.kind] || 0;
      m.progress = m.cumulative ? m.progress + value : Math.max(m.progress, value);
      if (m.progress >= m.goal) {
        summary.completed.push(m);
        summary.coins += m.reward;
      }
    }
    if (summary.completed.length) {
      save.missions = save.missions.filter((m) => summary.completed.indexOf(m) === -1);
      save.missionTier += summary.completed.length;
      fillMissions(save, rng || Math.random);
    }
    save.coins += summary.coins;
    return summary;
  }

  // Daily challenge: everyone gets the same stage on the same day (seed = hash of the date).
  function dailySeed(day) {
    let h = 2166136261;
    for (let i = 0; i < day.length; i++) h = Math.imul(h ^ day.charCodeAt(i), 16777619);
    return h >>> 0;
  }

  function dailyBest(save, day) {
    return save.daily && save.daily.day === day ? save.daily.best : 0;
  }

  // Returns { prevBest, best, newBest } for today's challenge.
  function recordDaily(save, day, score) {
    if (!save.daily || save.daily.day !== day) save.daily = { day, best: 0, tries: 0 };
    const prevBest = save.daily.best;
    save.daily.tries++;
    if (score > prevBest) save.daily.best = score;
    return { prevBest, best: save.daily.best, newBest: prevBest > 0 && score > prevBest };
  }

  function buySkin(save, id) {
    const skin = SKINS.find((s) => s.id === id);
    if (!skin) return false;
    if (save.owned.indexOf(id) !== -1) {
      save.skin = id;
      return true;
    }
    if (save.coins < skin.price) return false;
    save.coins -= skin.price;
    save.owned.push(id);
    save.skin = id;
    return true;
  }

  return { KEY, dailySeed, dailyBest, recordDaily, SKINS, runCoins, xpForLevel, MISSION_POOL, defaultSave, sanitize, load, persist, levelFromXp, levelProgress, checkDaily, applyRun, buySkin, today, dayDiff };
});
