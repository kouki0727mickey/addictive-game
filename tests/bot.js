// A simple autopilot used to check that generated levels are survivable.
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

function play(seed, maxTime) {
  const s = Core.createGame(seed);
  const dt = 1 / 60;
  while (s.alive && s.t < maxTime) {
    if (decide(s)) Core.switchRing(s);
    Core.step(s, dt);
    Core.drainEvents(s);
  }
  return s;
}

module.exports = { decide, play };
