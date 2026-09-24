import XCTest
@testable import OrbitSwitch

final class GameCoreTests: XCTestCase {
    // Reference values produced by the web version (js/core.js, js/meta.js).
    // If these match, iOS and the browser generate identical stages (same daily challenge).
    func testRandomMatchesWebVersion() {
        var r = Mulberry32(seed: 42)
        XCTAssertEqual(r.next(), 0.6011037519201636, accuracy: 1e-15)
        XCTAssertEqual(r.next(), 0.44829055899754167, accuracy: 1e-15)
        XCTAssertEqual(r.next(), 0.8524657934904099, accuracy: 1e-15)
    }

    func testDailySeedMatchesWebVersion() {
        XCTAssertEqual(Meta.dailySeed("2026-9-24"), 2_659_934_906)
    }

    func testSimulationMatchesWebVersion() {
        let s = GameState(seed: 12345)
        var i = 0
        while i < 60 * 20 && s.alive {
            if s.autopilotWantsSwitch() { s.switchRing() }
            s.step(1.0 / 60)
            _ = s.drainEvents()
            i += 1
        }
        XCTAssertTrue(s.alive)
        XCTAssertEqual(s.score, 56)
        XCTAssertEqual(s.gems, 6)
        XCTAssertEqual(s.passedSpikes, 29)
        let expected: [(Int, ObjectKind, Int, Double)] = [
            (40, .spike, 1, 31.663206077), (41, .spike, 1, 31.803206077), (42, .spike, 1, 33.291084651),
            (43, .spike, 1, 33.431084651), (44, .spike, 0, 34.57795859),
        ]
        for (o, e) in zip(s.objects, expected) {
            XCTAssertEqual(o.id, e.0)
            XCTAssertEqual(o.kind, e.1)
            XCTAssertEqual(o.ring, e.2)
            XCTAssertEqual(o.angle, e.3, accuracy: 1e-6)
        }
    }

    func testIdlePlayerEventuallyDies() {
        let s = GameState(seed: 7)
        for _ in 0..<(60 * 60) where s.alive { s.step(1.0 / 60) }
        XCTAssertFalse(s.alive)
    }

    func testFirstSecondIsSafe() {
        for seed in UInt32(1)..<200 {
            let s = GameState(seed: seed)
            for _ in 0..<60 { s.step(1.0 / 60) }
            XCTAssertTrue(s.alive, "seed \(seed) died within 1s of doing nothing")
        }
    }

    func testSwitchRingMovesPlayer() {
        let s = GameState(seed: 1)
        s.switchRing()
        XCTAssertEqual(s.ring, 0)
        XCTAssertEqual(s.drainEvents().first, .switched(ring: 0))
        for _ in 0..<30 { s.step(1.0 / 60) }
        XCTAssertEqual(s.ringPos, 0)
    }

    /// A perfect autopilot must survive: levels never contain impossible patterns.
    func testLevelsAreFair() {
        var survived = 0
        for seed in UInt32(1)...40 {
            let s = GameState(seed: seed)
            while s.alive && s.t < 90 {
                if s.autopilotWantsSwitch() { s.switchRing() }
                s.step(1.0 / 60)
                _ = s.drainEvents()
            }
            if s.alive { survived += 1 }
        }
        XCTAssertGreaterThanOrEqual(survived, 39)
    }

    /// Nothing may be live more than the spawn horizon ahead (it would overlap the player a lap later).
    func testNoLapOverlap() {
        for seed in UInt32(1)...10 {
            let s = GameState(seed: seed)
            s.passedSpikes = Int(GameConfig.rampSpikes) // late-game patterns
            for _ in 0..<(60 * 30) where s.alive {
                if s.autopilotWantsSwitch() { s.switchRing() }
                s.step(1.0 / 60)
                for o in s.objects {
                    XCTAssertLessThan(o.angle - s.angle, GameConfig.spawnAhead + 1e-6)
                }
            }
        }
    }

    func testFeverEndGrantsGrace() {
        let s = GameState(seed: 3)
        s.fever = 0.001
        s.step(1.0 / 60)
        XCTAssertGreaterThan(s.grace, 0)
        s.objects.append(OrbitObject(id: 999, kind: .spike, ring: s.ring, angle: s.angle))
        s.step(1.0 / 120)
        XCTAssertTrue(s.alive)
    }

    func testSpeedRampsWithSpikesNotScore() {
        let s = GameState(seed: 5)
        s.score = 10_000
        s.step(1.0 / 60)
        XCTAssertEqual(s.speed, GameConfig.baseSpeed, accuracy: 1e-9)
        s.passedSpikes = Int(GameConfig.rampSpikes)
        s.step(1.0 / 60)
        XCTAssertEqual(s.speed, GameConfig.maxSpeed, accuracy: 1e-9)
    }
}
