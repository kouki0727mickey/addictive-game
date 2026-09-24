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

  const SKINS = [
    { id: 'neon', name: 'ネオン', price: 0, color: '#4df3ff', trail: '#4df3ff' },
    { id: 'sakura', name: 'サクラ', price: 60, color: '#ff7ad9', trail: '#ffb3ec' },
    { id: 'lime', name: 'ライム', price: 120, color: '#b6ff4d', trail: '#e2ff9e' },
    { id: 'sun', name: 'サン', price: 200, color: '#ffc94d', trail: '#ff7b3a' },
    { id: 'void', name: 'ヴォイド', price: 350, color: '#b28cff', trail: '#6a3dff' },
    { id: 'rainbow', name: 'レインボー', price: 600, color: 'rainbow', trail: 'rainbow' },
  ];

  const MISSION_POOL = [
    { kind: 'score', goals: [20, 40, 70, 100, 150], text: 'ワンプレイで{n}点' },
    { kind: 'gems', goals: [5, 10, 20, 35], text: 'ワンプレイでジェム{n}個' },
    { kind: 'nearMisses', goals: [2, 4, 8], text: 'ワンプレイでニアミス{n}回' },
    { kind: 'bestCombo', goals: [5, 10, 20], text: 'コンボ{n}達成' },
    { kind: 'feverCount', goals: [1, 2, 3], text: 'ワンプレイでフィーバー{n}回' },
    { kind: 'plays', goals: [3, 5, 10], text: '{n}回プレイ', cumulative: true },
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
    };
  }

  function makeMission(save, rng, excludeKinds) {
    const pool = MISSION_POOL.filter((m) => excludeKinds.indexOf(m.kind) === -1);
    const m = pool[Math.floor(rng() * pool.length)];
    const tier = Math.min(m.goals.length - 1, Math.floor(save.missionTier / 2));
    const goal = m.goals[tier];
    return { kind: m.kind, goal, progress: 0, reward: 15 + tier * 15, text: m.text.replace('{n}', goal), cumulative: !!m.cumulative };
  }

  function fillMissions(save, rng) {
    while (save.missions.length < 3) {
      save.missions.push(makeMission(save, rng, save.missions.map((m) => m.kind)));
    }
  }

  function load(storage, rng) {
    let save = defaultSave();
    try {
      const raw = storage && storage.getItem(KEY);
      if (raw) save = Object.assign(save, JSON.parse(raw));
    } catch (e) {
      /* corrupt or unavailable storage: start fresh */
    }
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

  function levelFromXp(xp) {
    // Level n needs 50 * n * (n + 1) / 2 cumulative xp
    let lvl = 1;
    while (xp >= (50 * lvl * (lvl + 1)) / 2) lvl++;
    return lvl;
  }

  function levelProgress(xp) {
    const lvl = levelFromXp(xp);
    const prev = (50 * (lvl - 1) * lvl) / 2;
    const next = (50 * lvl * (lvl + 1)) / 2;
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

  // Apply the result of a run. Returns a summary for the game-over screen.
  function applyRun(save, run, rng) {
    const summary = { newBest: false, coins: 0, levelUps: 0, completed: [], prevBest: save.best };
    save.plays++;
    save.totalGems += run.gems;
    if (run.score > save.best) {
      save.best = run.score;
      summary.newBest = summary.prevBest > 0;
    }
    const earned = Math.floor(run.score / 4) + run.gems;
    summary.coins += earned;

    const lvlBefore = levelFromXp(save.xp);
    save.xp += run.score;
    const lvlAfter = levelFromXp(save.xp);
    summary.levelUps = lvlAfter - lvlBefore;
    summary.coins += summary.levelUps * 25;

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

  return { KEY, SKINS, MISSION_POOL, defaultSave, load, persist, levelFromXp, levelProgress, checkDaily, applyRun, buySkin, today, dayDiff };
});
