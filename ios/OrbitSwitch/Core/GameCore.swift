// ORBIT SWITCH — core simulation (Swift port of js/core.js).
// Pure logic: no UIKit / SpriteKit, so it is unit-testable and deterministic for a given seed.
// The random generator and level generator match the web version, so the daily challenge
// produces the same stage on iOS and in the browser.

import Foundation

enum GameConfig {
    static let ringRadius: [Double] = [0.26, 0.4] // inner, outer (fraction of the short screen side)
    static let playerRadius = 0.022
    static let spikeRadius = 0.022
    static let gemRadius = 0.018
    static let hitForgiveness = 0.75 // spike hitbox scale: <1 makes spikes smaller than they look
    static let gemMagnet = 1.6 // gem pickup radius scale: >1 makes gems easier to grab
    static let passBehind = 0.06 // radians behind the player at which an object counts as passed
    static let baseSpeed = 1.5 // rad/s
    static let maxSpeed = 3.4
    static let rampSpikes = 150.0 // spikes passed until top speed
    static let switchTime = 0.11 // seconds to move between rings
    static let spawnAhead = Double.pi * 1.35
    static let despawnBehind = 0.8
    static let nearMissWindow = 0.28 // seconds since last switch
    static let feverEvery = 10 // combo count that triggers fever
    static let feverDuration = 4.0
    static let feverGrace = 0.6 // seconds of invulnerability after fever ends
    static let maxMultiplier = 5
    static let maxStep = 1.0 / 120.0
}

/// Same algorithm as the web version's mulberry32 (32-bit wrapping arithmetic).
struct Mulberry32 {
    private var a: UInt32

    init(seed: UInt32) { a = seed }

    mutating func next() -> Double {
        a = a &+ 0x6D2B_79F5
        var t = a
        t = (t ^ (t >> 15)) &* (t | 1)
        t ^= t &+ ((t ^ (t >> 7)) &* (t | 61))
        return Double(t ^ (t >> 14)) / 4_294_967_296.0
    }
}

enum ObjectKind { case spike, gem }

struct OrbitObject {
    let id: Int
    let kind: ObjectKind
    let ring: Int
    let angle: Double
    var passed = false
    var dead = false
}

struct Vec2 {
    var x: Double
    var y: Double
}

enum GameEvent: Equatable {
    case switched(ring: Int)
    case gem(x: Double, y: Double, combo: Int, points: Int)
    case nearMiss(x: Double, y: Double)
    case smash(x: Double, y: Double)
    case fever
    case feverEnd
    case comboLost(combo: Int)
    case death(x: Double, y: Double)
}

@inline(__always) private func lerp(_ a: Double, _ b: Double, _ t: Double) -> Double { a + (b - a) * t }

final class GameState {
    let seed: UInt32
    private var rng: Mulberry32

    private(set) var t = 0.0
    private(set) var angle = -Double.pi / 2
    private(set) var ring = 1
    private(set) var ringPos = 1.0
    private(set) var lastSwitchT = -10.0
    private(set) var speed = GameConfig.baseSpeed
    var score = 0
    private(set) var combo = 0
    private(set) var bestCombo = 0
    private(set) var gems = 0
    private(set) var nearMisses = 0
    var fever = 0.0
    private(set) var grace = 0.0
    private(set) var feverCount = 0
    private(set) var smashed = 0
    var passedSpikes = 0
    private(set) var alive = true
    var objects: [OrbitObject] = []
    private(set) var pending: [OrbitObject] = []
    private var nextId = 1
    private var nextSpawnAngle = -Double.pi / 2 + 1.6
    private var lastSpikeRing = -1
    private var lastSpikeAngle = -Double.infinity
    private var events: [GameEvent] = []

    init(seed: UInt32) {
        self.seed = seed
        rng = Mulberry32(seed: seed)
    }

    // MARK: derived values

    /// 0...1, driven by spikes passed (not score) so gems/multipliers don't make it suddenly faster.
    var difficulty: Double { min(1, max(0, Double(passedSpikes) / GameConfig.rampSpikes)) }

    var multiplier: Int { min(GameConfig.maxMultiplier, 1 + combo / 5) }

    var effectiveMultiplier: Int { multiplier * (fever > 0 ? 2 : 1) }

    static func ringRadius(_ ringPos: Double) -> Double {
        lerp(GameConfig.ringRadius[0], GameConfig.ringRadius[1], ringPos)
    }

    var playerPos: Vec2 {
        let r = GameState.ringRadius(ringPos)
        return Vec2(x: cos(angle) * r, y: sin(angle) * r)
    }

    static func position(of o: OrbitObject) -> Vec2 {
        let r = GameConfig.ringRadius[o.ring]
        return Vec2(x: cos(o.angle) * r, y: sin(o.angle) * r)
    }

    // MARK: input

    func switchRing() {
        guard alive else { return }
        ring = 1 - ring
        lastSwitchT = t
        events.append(.switched(ring: ring))
    }

    func drainEvents() -> [GameEvent] {
        let e = events
        events.removeAll(keepingCapacity: true)
        return e
    }

    // MARK: level generation

    // Patterns can extend far ahead. Objects wait in `pending` (sorted by angle) and only become live
    // once inside the spawn horizon, so nothing is ever placed a full lap ahead, where it would
    // physically overlap the player's current position.
    private func addObject(_ kind: ObjectKind, ring: Int, angle: Double) {
        let o = OrbitObject(id: nextId, kind: kind, ring: ring, angle: angle)
        nextId += 1
        var i = pending.count
        while i > 0 && pending[i - 1].angle > angle { i -= 1 }
        pending.insert(o, at: i)
    }

    // Place one "beat" of content at nextSpawnAngle and advance it.
    // The order of rng() calls mirrors the web version exactly.
    private func spawnBeat() {
        let d = difficulty
        let minGap = lerp(0.62, 0.36, d)
        let gapT = minGap + rng.next() * lerp(0.35, 0.18, d)
        let a = nextSpawnAngle
        let roll = rng.next()

        if roll < 0.62 {
            // single spike, gem on the safe ring sometimes
            var r = rng.next() < 0.5 ? 0 : 1
            if lastSpikeRing != -1 && r != lastSpikeRing {
                // switching required: guarantee enough reaction time
                if a - lastSpikeAngle < minGap * speed { r = lastSpikeRing }
            }
            addObject(.spike, ring: r, angle: a)
            lastSpikeRing = r
            lastSpikeAngle = a
            if rng.next() < 0.45 { addObject(.gem, ring: 1 - r, angle: a) }
            nextSpawnAngle = a + gapT * speed
        } else if roll < 0.72 && d > 0.3 {
            // zigzag: alternating spikes at the tightest fair spacing
            let n = 3 + Int(floor(rng.next() * 2))
            let zigGap = minGap * speed
            var r = lastSpikeRing == -1 ? 0 : lastSpikeRing
            var at = max(a, lastSpikeAngle + zigGap)
            for _ in 0..<n {
                addObject(.spike, ring: r, angle: at)
                if rng.next() < 0.5 { addObject(.gem, ring: 1 - r, angle: at) }
                lastSpikeRing = r
                lastSpikeAngle = at
                r = 1 - r
                at += zigGap
            }
            nextSpawnAngle = lastSpikeAngle + gapT * speed
        } else if roll < 0.82 {
            // gem trail on one ring
            let r = rng.next() < 0.5 ? 0 : 1
            let n = 3
            let step = 0.16
            for i in 0..<n { addObject(.gem, ring: r, angle: a + Double(i) * step) }
            nextSpawnAngle = a + Double(n) * step + gapT * speed * 0.5
        } else {
            // double spike on the same ring (stay put or switch early)
            let r = lastSpikeRing == -1 ? 1 : lastSpikeRing
            addObject(.spike, ring: r, angle: a)
            addObject(.spike, ring: r, angle: a + 0.14)
            lastSpikeRing = r
            lastSpikeAngle = a + 0.14
            nextSpawnAngle = a + 0.14 + gapT * speed
        }
    }

    // MARK: simulation

    func step(_ dt: Double) {
        guard alive else { return }
        var left = min(dt, 0.1)
        while left > 0 && alive {
            let h = min(left, GameConfig.maxStep)
            subStep(h)
            left -= h
        }
    }

    private func subStep(_ dt: Double) {
        t += dt
        let dir = Double(ring) - ringPos
        let move = dt / GameConfig.switchTime
        ringPos = abs(dir) <= move ? Double(ring) : ringPos + (dir > 0 ? move : -move)

        speed = lerp(GameConfig.baseSpeed, GameConfig.maxSpeed, difficulty)
        angle += speed * dt

        if grace > 0 { grace = max(0, grace - dt) }
        if fever > 0 {
            fever = max(0, fever - dt)
            if fever == 0 {
                // Don't let fever end *inside* a spike: give a short invulnerable window.
                grace = GameConfig.feverGrace
                events.append(.feverEnd)
            }
        }

        let horizon = angle + GameConfig.spawnAhead
        while nextSpawnAngle < horizon { spawnBeat() }
        while let first = pending.first, first.angle < horizon {
            objects.append(pending.removeFirst())
        }

        let p = playerPos
        let mult = effectiveMultiplier
        for i in objects.indices {
            if objects[i].dead { continue }
            let o = objects[i]
            let q = GameState.position(of: o)
            let dx = p.x - q.x
            let dy = p.y - q.y
            let isGem = o.kind == .gem
            // Right after fever, spikes are harmless (but still count as passed below).
            let harmless = !isGem && grace > 0
            if !harmless {
                let rr = isGem
                    ? GameConfig.playerRadius + GameConfig.gemRadius * GameConfig.gemMagnet
                    : (GameConfig.playerRadius + GameConfig.spikeRadius) * GameConfig.hitForgiveness
                if dx * dx + dy * dy < rr * rr {
                    if isGem {
                        objects[i].dead = true
                        gems += 1
                        combo += 1
                        bestCombo = max(bestCombo, combo)
                        let points = 2 * mult
                        score += points
                        events.append(.gem(x: q.x, y: q.y, combo: combo, points: points))
                        if combo % GameConfig.feverEvery == 0 {
                            fever = GameConfig.feverDuration
                            feverCount += 1
                            events.append(.fever)
                        }
                    } else if fever > 0 {
                        objects[i].dead = true
                        smashed += 1
                        score += 3 * mult
                        events.append(.smash(x: q.x, y: q.y))
                    } else {
                        alive = false
                        events.append(.death(x: p.x, y: p.y))
                        return
                    }
                    continue
                }
            }
            let rel = o.angle - angle
            if !o.passed && rel < -GameConfig.passBehind {
                objects[i].passed = true
                if o.kind == .spike {
                    passedSpikes += 1
                    score += mult
                    if o.ring != ring && t - lastSwitchT < GameConfig.nearMissWindow {
                        nearMisses += 1
                        score += 2 * mult
                        events.append(.nearMiss(x: q.x, y: q.y))
                    }
                } else {
                    if combo > 0 { events.append(.comboLost(combo: combo)) }
                    combo = 0
                }
            }
        }
        let a = angle
        objects.removeAll { $0.dead || $0.angle - a <= -GameConfig.despawnBehind }
    }

    // MARK: autopilot

    /// Switch when a spike on our ring is close and the other ring is clearer.
    /// Used by the menu's attract-mode demo and the fairness tests.
    func autopilotWantsSwitch(extraLead: Double = 0) -> Bool {
        guard alive, ringPos == Double(ring) else { return false }
        let horizon = speed * (GameConfig.switchTime + 0.12 + extraLead)
        var threatCur = Double.infinity
        var threatOther = Double.infinity
        for o in objects where o.kind == .spike && !o.dead {
            let rel = o.angle - angle
            if rel < -0.12 { continue }
            if o.ring == ring { threatCur = min(threatCur, rel) } else { threatOther = min(threatOther, rel) }
        }
        return threatCur < horizon && threatOther > threatCur + 0.1
    }
}
