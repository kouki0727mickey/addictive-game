// Autopilots used to check that generated levels are survivable.
const Core = require('../js/core.js');

function decide(s, extraLead) {
  return Core.autopilot(s, extraLead);
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
    const want = queue.length === 0 && decide(s, reaction);
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
