// Autopilots used to check that generated levels are survivable.
const Core = require('../js/core.js');

// Returns true if the player should switch rings now.
function decide(s) {
  const C = Core.CONFIG;
  const cur = s.ring;
  const horizon = s.speed * (C.switchTime + 0.12);
  let threatCur = Infinity;
  let threatOther = Infinity;
  for (const o of s.objects) {
    if (o.type !== 'spike' || o.dead) continue;
    const rel = o.angle - s.angle;
    if (rel < -0.12) continue;
    if (o.ring === cur) threatCur = Math.min(threatCur, rel);
    else threatOther = Math.min(threatOther, rel);
  }
  if (s.ringPos !== s.ring) return false; // mid-switch
  return threatCur < horizon && threatOther > threatCur + 0.1;
}

// Perfect-information bot: reacts instantly.
function play(seed, maxTime) {
  return playHuman(seed, maxTime, 0);
}

// "Human" bot: its decisions reach the game `reaction` seconds late,
// and it plans with a longer look-ahead to compensate (like a person would).
// `jitter` adds uniform timing error of ±jitter seconds to every tap.
function playHuman(seed, maxTime, reaction, jitter) {
  const s = Core.createGame(seed);
  const noise = Core.mulberry32(seed * 7919 + 1);
  const dt = 1 / 60;
  const queue = []; // times at which a queued tap fires
  let plannedRing = s.ring;
  while (s.alive && s.t < maxTime) {
    // plan against the ring we will be on once queued taps land
    const real = s.ring;
    s.ring = plannedRing;
    const saved = s.ringPos;
    s.ringPos = plannedRing;
    const C = Core.CONFIG;
    const sw = C.switchTime;
    C.switchTime = sw + reaction;
    const want = queue.length === 0 && decide(s);
    C.switchTime = sw;
    s.ring = real;
    s.ringPos = saved;
    if (want) {
      queue.push(s.t + reaction + (jitter ? (noise() * 2 - 1) * jitter : 0));
      queue.sort((a, b) => a - b);
      plannedRing = 1 - plannedRing;
    }
    while (queue.length && queue[0] <= s.t + 1e-9) {
      queue.shift();
      Core.switchRing(s);
    }
    Core.step(s, dt);
    Core.drainEvents(s);
  }
  return s;
}

module.exports = { decide, play, playHuman };
