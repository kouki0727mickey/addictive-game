import XCTest
@testable import OrbitSwitch

final class MetaTests: XCTestCase {
    private let rng: () -> Double = { 0.3 }

    private func freshDefaults() -> UserDefaults {
        let name = "test-\(UUID().uuidString)"
        let d = UserDefaults(suiteName: name)!
        d.removePersistentDomain(forName: name)
        return d
    }

    func testLoadGivesThreeDistinctMissions() {
        let s = Meta.load(defaults: freshDefaults(), rng: rng)
        XCTAssertEqual(s.best, 0)
        XCTAssertEqual(s.missions.count, 3)
        XCTAssertEqual(Set(s.missions.map(\.kind)).count, 3)
    }

    func testPersistRoundTrip() {
        let d = freshDefaults()
        var s = Meta.load(defaults: d, rng: rng)
        s.coins = 77
        s.hapticsOn = false
        Meta.persist(s, defaults: d)
        let back = Meta.load(defaults: d, rng: rng)
        XCTAssertEqual(back.coins, 77)
        XCTAssertFalse(back.hapticsOn)
    }

    func testCorruptSaveFallsBackToDefaults() throws {
        let json = #"{"coins":"lots","best":-5,"owned":"neon","skin":"hacker","missions":[{"kind":"nope"}]}"#
        let s = try JSONDecoder().decode(SaveData.self, from: Data(json.utf8))
        XCTAssertEqual(s.coins, 0)
        XCTAssertEqual(s.best, 0)
        XCTAssertEqual(s.owned, ["neon"])
        XCTAssertEqual(s.skin, "neon")
        XCTAssertTrue(s.missions.isEmpty)
    }

    func testApplyRunUpdatesBestAndCoins() {
        var s = Meta.load(defaults: freshDefaults(), rng: rng)
        let r1 = Meta.applyRun(&s, RunResult(score: 40, gems: 5, nearMisses: 0, bestCombo: 3, feverCount: 0), rng: rng)
        XCTAssertEqual(s.best, 40)
        XCTAssertFalse(r1.newBest) // the first run is not celebrated as a "new best"
        let r2 = Meta.applyRun(&s, RunResult(score: 41, gems: 0, nearMisses: 0, bestCombo: 0, feverCount: 0), rng: rng)
        XCTAssertTrue(r2.newBest)
    }

    func testLevels() {
        XCTAssertEqual(Meta.level(xp: 0), 1)
        XCTAssertEqual(Meta.level(xp: Meta.xpForLevel(1) - 1), 1)
        XCTAssertEqual(Meta.level(xp: Meta.xpForLevel(1)), 2)
        let p = Meta.levelProgress(xp: Meta.xpForLevel(1) + 5)
        XCTAssertEqual(p.level, 2)
        XCTAssertEqual(p.into, 5)
    }

    func testDailyBonusStreak() {
        var s = SaveData()
        let cal = Calendar.current
        let t0 = cal.date(from: DateComponents(year: 2026, month: 1, day: 1, hour: 12))!
        XCTAssertEqual(Meta.checkDaily(&s, now: t0), 10)
        XCTAssertEqual(Meta.checkDaily(&s, now: t0.addingTimeInterval(60)), 0)
        XCTAssertEqual(Meta.checkDaily(&s, now: cal.date(byAdding: .day, value: 1, to: t0)!), 15)
        XCTAssertEqual(s.streak, 2)
        XCTAssertEqual(Meta.checkDaily(&s, now: cal.date(byAdding: .day, value: 3, to: t0)!), 10)
        XCTAssertEqual(s.streak, 1)
    }

    func testBuySkin() {
        var s = SaveData()
        XCTAssertFalse(Meta.buySkin(&s, id: "sakura"))
        s.coins = 100
        XCTAssertTrue(Meta.buySkin(&s, id: "sakura"))
        XCTAssertEqual(s.coins, 20)
        XCTAssertEqual(s.skin, "sakura")
        XCTAssertTrue(Meta.buySkin(&s, id: "neon"))
        XCTAssertEqual(s.coins, 20)
    }

    func testBeginnerUnlocksFirstSkinIn3To8Runs() {
        var s = Meta.load(defaults: freshDefaults(), rng: rng)
        let first = Skins.all.filter { $0.price > 0 }.min { $0.price < $1.price }!
        var runs = 0
        while s.coins < first.price && runs < 50 {
            _ = Meta.applyRun(&s, RunResult(score: 20, gems: 3, nearMisses: 1, bestCombo: 2, feverCount: 0), rng: rng)
            runs += 1
        }
        XCTAssertTrue((3...8).contains(runs), "first skin after \(runs) runs")
    }

    func testMonsterRunCannotBuyTheShop() {
        var s = Meta.load(defaults: freshDefaults(), rng: rng)
        let r = Meta.applyRun(&s, RunResult(score: 5000, gems: 300, nearMisses: 80, bestCombo: 100, feverCount: 10), rng: rng)
        let total = Skins.all.reduce(0) { $0 + $1.price }
        XCTAssertLessThan(Double(r.coins), Double(total) * 0.2)
    }

    func testDailyChallengeRecords() {
        var s = SaveData()
        var r = Meta.recordDaily(&s, day: "2026-9-24", score: 30)
        XCTAssertEqual(r.best, 30)
        XCTAssertFalse(r.newBest)
        r = Meta.recordDaily(&s, day: "2026-9-24", score: 45)
        XCTAssertTrue(r.newBest)
        XCTAssertEqual(s.daily?.tries, 2)
        XCTAssertEqual(Meta.dailyBest(s, day: "2026-9-25"), 0)
    }
}
