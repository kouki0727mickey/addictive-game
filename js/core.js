/*
 * ORBIT SWITCH — core simulation.
 * Pure logic, no DOM. Works in the browser (window.OrbitCore) and in Node (require).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.OrbitCore = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const TAU = Math.PI * 2;

  const CONFIG = {
    ringRadius: [0.26, 0.4], // inner, outer (fraction of the short screen side)
    playerRadius: 0.022,
    spikeRadius: 0.022,
    gemRadius: 0.018,
    hitForgiveness: 0.75, // spike hitbox scale: <1 makes spikes smaller than they look
    gemMagnet: 1.6, // gem pickup radius scale: >1 makes gems easier to grab than they look
    passBehind: 0.06, // radians behind the player at which an object counts as passed
    baseSpeed: 1.5, // rad/s
    maxSpeed: 3.4,
    rampSpikes: 150, // spikes passed until top speed
    switchTime: 0.11, // seconds to move between rings
    spawnAhead: Math.PI * 1.35,
    despawnBehind: 0.8,
    nearMissWindow: 0.28, // seconds since last switch
    feverEvery: 10, // combo count that triggers fever
    feverDuration: 4,
    feverGrace: 0.6, // seconds of invulnerability after fever ends
    maxMultiplier: 5,
    maxStep: 1 / 120,
  };

  function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function clamp(v, lo, hi) {
    return v < lo ? lo : v > hi ? hi : v;
  }

  function createGame(seed) {
    const s = {
      seed: seed >>> 0,
      rng: mulberry32(seed),
      t: 0,
      angle: -Math.PI / 2,
      ring: 1,
      ringPos: 1,
      lastSwitchT: -10,
      speed: CONFIG.baseSpeed,
      score: 0,
      combo: 0,
      bestCombo: 0,
      gems: 0,
      nearMisses: 0,
      fever: 0,
      grace: 0,
      feverCount: 0,
      smashed: 0,
      passedSpikes: 0,
      alive: true,
      objects: [],
      pending: [],
      nextId: 1,
      nextSpawnAngle: -Math.PI / 2 + 1.6,
      lastSpikeRing: -1,
      lastSpikeAngle: -Infinity,
      events: [],
    };
    return s;
  }

  // 0..1, driven by how far you've got (spikes passed) rather than score,
  // so collecting gems/multipliers doesn't make the game suddenly faster.
  function difficulty(s) {
    return clamp(s.passedSpikes / CONFIG.rampSpikes, 0, 1);
  }

  function multiplier(s) {
    return Math.min(CONFIG.maxMultiplier, 1 + Math.floor(s.combo / 5));
  }

  // Patterns can extend far ahead. Objects wait in `pending` (sorted by angle) and only become live
  // once inside the spawn horizon, so nothing can ever be placed a full lap ahead — where it would
  // physically overlap the player's current position.
  function addObject(s, type, ring, angle) {
    const o = { id: s.nextId++, type, ring, angle, passed: false, dead: false };
    let i = s.pending.length;
    while (i > 0 && s.pending[i - 1].angle > angle) i--;
    s.pending.splice(i, 0, o);
  }

  // Place one "beat" of content at s.nextSpawnAngle and advance it.
  function spawnBeat(s) {
    const d = difficulty(s);
    const rng = s.rng;
    const speed = s.speed;
    // Time gap between beats, converted to angle at current speed.
    const minGap = lerp(0.62, 0.36, d);
    const gapT = minGap + rng() * lerp(0.35, 0.18, d);
    const a = s.nextSpawnAngle;
    const roll = rng();

    if (roll < 0.62) {
      // single spike, gem on the safe ring sometimes
      let ring = rng() < 0.5 ? 0 : 1;
      if (s.lastSpikeRing !== -1 && ring !== s.lastSpikeRing) {
        // switching required: guarantee enough reaction time
        const needed = minGap * speed;
        if (a - s.lastSpikeAngle < needed) ring = s.lastSpikeRing;
      }
      addObject(s, 'spike', ring, a);
      s.lastSpikeRing = ring;
      s.lastSpikeAngle = a;
      if (rng() < 0.45) addObject(s, 'gem', 1 - ring, a);
    } else if (roll < 0.72 && d > 0.3) {
      // zigzag: alternating spikes at the tightest fair spacing, a rhythm test for later stages
      const n = 3 + Math.floor(rng() * 2);
      const zigGap = minGap * speed;
      let ring = s.lastSpikeRing === -1 ? 0 : s.lastSpikeRing;
      let at = Math.max(a, s.lastSpikeAngle + zigGap);
      for (let i = 0; i < n; i++) {
        addObject(s, 'spike', ring, at);
        if (rng() < 0.5) addObject(s, 'gem', 1 - ring, at);
        s.lastSpikeRing = ring;
        s.lastSpikeAngle = at;
        ring = 1 - ring;
        at += zigGap;
      }
      s.nextSpawnAngle = s.lastSpikeAngle + gapT * speed;
      return;
    } else if (roll < 0.82) {
      // gem trail on one ring
      const ring = rng() < 0.5 ? 0 : 1;
      const n = 3;
      const step = 0.16;
      for (let i = 0; i < n; i++) addObject(s, 'gem', ring, a + i * step);
      s.nextSpawnAngle = a + n * step + gapT * speed * 0.5;
      return;
    } else {
      // double spike on the same ring (stay put or switch early)
      const ring = s.lastSpikeRing === -1 ? 1 : s.lastSpikeRing;
      addObject(s, 'spike', ring, a);
      addObject(s, 'spike', ring, a + 0.14);
      s.lastSpikeRing = ring;
      s.lastSpikeAngle = a + 0.14;
      s.nextSpawnAngle = a + 0.14 + gapT * speed;
      return;
    }
    s.nextSpawnAngle = a + gapT * speed;
  }

  function ringRadius(ringPos) {
    return lerp(CONFIG.ringRadius[0], CONFIG.ringRadius[1], ringPos);
  }

  function playerPos(s) {
    const r = ringRadius(s.ringPos);
    return { x: Math.cos(s.angle) * r, y: Math.sin(s.angle) * r };
  }

  function objectPos(o) {
    const r = CONFIG.ringRadius[o.ring];
    return { x: Math.cos(o.angle) * r, y: Math.sin(o.angle) * r };
  }

  function emit(s, type, data) {
    s.events.push(Object.assign({ type }, data || {}));
  }

  function switchRing(s) {
    if (!s.alive) return;
    s.ring = 1 - s.ring;
    s.lastSwitchT = s.t;
    emit(s, 'switch', { ring: s.ring });
  }

  function subStep(s, dt) {
    s.t += dt;
    // ring interpolation
    const dir = s.ring - s.ringPos;
    const move = dt / CONFIG.switchTime;
    s.ringPos = Math.abs(dir) <= move ? s.ring : s.ringPos + Math.sign(dir) * move;

    s.speed = lerp(CONFIG.baseSpeed, CONFIG.maxSpeed, difficulty(s));
    s.angle += s.speed * dt;

    if (s.grace > 0) s.grace = Math.max(0, s.grace - dt);
    if (s.fever > 0) {
      s.fever = Math.max(0, s.fever - dt);
      if (s.fever === 0) {
        // Don't let fever end *inside* a spike: give a short invulnerable window.
        s.grace = CONFIG.feverGrace;
        emit(s, 'feverEnd');
      }
    }

    const horizon = s.angle + CONFIG.spawnAhead;
    while (s.nextSpawnAngle < horizon) spawnBeat(s);
    while (s.pending.length && s.pending[0].angle < horizon) s.objects.push(s.pending.shift());

    const p = playerPos(s);
    const mult = multiplier(s) * (s.fever > 0 ? 2 : 1);
    for (const o of s.objects) {
      if (o.dead) continue;
      const q = objectPos(o);
      const dx = p.x - q.x;
      const dy = p.y - q.y;
      const isGem = o.type === 'gem';
      // Right after fever, spikes are harmless (but still count as passed below).
      const harmless = !isGem && s.grace > 0;
      if (!harmless) {
        const rr = isGem ? CONFIG.playerRadius + CONFIG.gemRadius * CONFIG.gemMagnet : (CONFIG.playerRadius + CONFIG.spikeRadius) * CONFIG.hitForgiveness;
        if (dx * dx + dy * dy < rr * rr) {
          if (o.type === 'gem') {
            o.dead = true;
            s.gems++;
            s.combo++;
            s.bestCombo = Math.max(s.bestCombo, s.combo);
            const points = 2 * mult;
            s.score += points;
            emit(s, 'gem', { x: q.x, y: q.y, combo: s.combo, points });
            if (s.combo % CONFIG.feverEvery === 0) {
              s.fever = CONFIG.feverDuration;
              s.feverCount++;
              emit(s, 'fever');
            }
          } else if (s.fever > 0) {
            o.dead = true;
            s.smashed++;
            s.score += 3 * mult;
            emit(s, 'smash', { x: q.x, y: q.y });
          } else {
            s.alive = false;
            emit(s, 'death', { x: p.x, y: p.y });
            return;
          }
          continue;
        }
      }
      const rel = o.angle - s.angle;
      if (!o.passed && rel < -CONFIG.passBehind) {
        o.passed = true;
        if (o.type === 'spike') {
          s.passedSpikes++;
          s.score += mult;
          if (o.ring !== s.ring && s.t - s.lastSwitchT < CONFIG.nearMissWindow) {
            s.nearMisses++;
            s.score += 2 * mult;
            emit(s, 'nearMiss', { x: q.x, y: q.y });
          }
        } else {
          if (s.combo > 0) emit(s, 'comboLost', { combo: s.combo });
          s.combo = 0;
        }
      }
    }
    // Compact in place: this runs up to 120 times a second, so avoid allocating a new array.
    let w = 0;
    for (let i = 0; i < s.objects.length; i++) {
      const o = s.objects[i];
      if (!o.dead && o.angle - s.angle > -CONFIG.despawnBehind) s.objects[w++] = o;
    }
    s.objects.length = w;
  }

  function step(s, dt) {
    if (!s.alive) return;
    let left = Math.min(dt, 0.1);
    while (left > 0 && s.alive) {
      const h = Math.min(left, CONFIG.maxStep);
      subStep(s, h);
      left -= h;
    }
  }

  // Simple autopilot: switch when a spike on our ring is close and the other ring is clearer.
  // Used by the menu's attract-mode demo, the ?autoplay test hook and the fairness tests.
  function autopilot(s, extraLead) {
    if (!s.alive || s.ringPos !== s.ring) return false;
    const horizon = s.speed * (CONFIG.switchTime + 0.12 + (extraLead || 0));
    let threatCur = Infinity;
    let threatOther = Infinity;
    for (const o of s.objects) {
      if (o.type !== 'spike' || o.dead) continue;
      const rel = o.angle - s.angle;
      if (rel < -0.12) continue;
      if (o.ring === s.ring) threatCur = Math.min(threatCur, rel);
      else threatOther = Math.min(threatOther, rel);
    }
    return threatCur < horizon && threatOther > threatCur + 0.1;
  }

  function drainEvents(s) {
    const e = s.events;
    s.events = [];
    return e;
  }

  return {
    TAU,
    CONFIG,
    mulberry32,
    createGame,
    step,
    switchRing,
    drainEvents,
    autopilot,
    playerPos,
    objectPos,
    ringRadius,
    multiplier,
    difficulty,
  };
});
