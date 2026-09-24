// ORBIT SWITCH — meta progression (Swift port of js/meta.js):
// coins, skins, missions, level, daily bonus, daily challenge and the save file.

import Foundation

struct Skin: Identifiable, Equatable {
    let id: String
    let price: Int
    /// 0xRRGGBB, or nil for the animated rainbow skin
    let color: UInt32?
    let trail: UInt32?

    var name: String { L10n.t("skin.\(id)") }
}

enum Skins {
    static let all: [Skin] = [
        Skin(id: "neon", price: 0, color: 0x4DF3FF, trail: 0x4DF3FF),
        Skin(id: "sakura", price: 80, color: 0xFF7AD9, trail: 0xFFB3EC),
        Skin(id: "lime", price: 200, color: 0xB6FF4D, trail: 0xE2FF9E),
        Skin(id: "sun", price: 400, color: 0xFFC94D, trail: 0xFF7B3A),
        Skin(id: "void", price: 700, color: 0xB28CFF, trail: 0x6A3DFF),
        Skin(id: "ghost", price: 1100, color: 0xEEF2FF, trail: 0x8A90B8),
        Skin(id: "rainbow", price: 1600, color: nil, trail: nil),
    ]

    static func find(_ id: String) -> Skin { all.first { $0.id == id } ?? all[0] }
}

enum MissionKind: String, Codable, CaseIterable {
    case score, gems, nearMisses, bestCombo, feverCount, plays

    var goals: [Int] {
        switch self {
        case .score: return [20, 40, 70, 100, 150]
        case .gems: return [5, 10, 20, 35]
        case .nearMisses: return [2, 4, 8]
        case .bestCombo: return [5, 10, 20]
        case .feverCount: return [1, 2, 3]
        case .plays: return [3, 5, 10]
        }
    }

    var cumulative: Bool { self == .plays }

    func text(_ n: Int) -> String { L10n.t("mission.\(rawValue)", ["n": n]) }
}

struct Mission: Codable, Equatable, Identifiable {
    var id = UUID()
    let kind: MissionKind
    let goal: Int
    var progress: Int
    let reward: Int

    var text: String { kind.text(goal) }
}

struct DailyRecord: Codable, Equatable {
    var day: String
    var best: Int
    var tries: Int
}

/// Result of one run as fed into the meta layer.
struct RunResult {
    var score: Int
    var gems: Int
    var nearMisses: Int
    var bestCombo: Int
    var feverCount: Int

    func value(for kind: MissionKind) -> Int {
        switch kind {
        case .score: return score
        case .gems: return gems
        case .nearMisses: return nearMisses
        case .bestCombo: return bestCombo
        case .feverCount: return feverCount
        case .plays: return 1
        }
    }
}

struct RunSummary {
    var newBest = false
    var coins = 0
    var levelUps = 0
    var completed: [Mission] = []
    var prevBest = 0
}

struct SaveData: Codable, Equatable {
    var best = 0
    var coins = 0
    var xp = 0
    var plays = 0
    var totalGems = 0
    var skin = "neon"
    var owned = ["neon"]
    var missions: [Mission] = []
    var missionTier = 0
    var lastDay: String?
    var streak = 0
    var soundOn = true
    var hapticsOn = true
    var lang = "auto" // "auto" follows the device language; "ja" / "en" are explicit choices
    var daily: DailyRecord?

    init() {}

    // Tolerant decoding: any missing or broken field falls back to its default,
    // so an old or corrupt save never crashes the app or wipes everything.
    init(from decoder: Decoder) throws {
        self.init()
        guard let c = try? decoder.container(keyedBy: CodingKeys.self) else { return }
        func int(_ k: CodingKeys) -> Int? {
            guard let v = try? c.decodeIfPresent(Int.self, forKey: k), v >= 0 else { return nil }
            return v
        }
        best = int(.best) ?? 0
        coins = int(.coins) ?? 0
        xp = int(.xp) ?? 0
        plays = int(.plays) ?? 0
        totalGems = int(.totalGems) ?? 0
        missionTier = int(.missionTier) ?? 0
        streak = int(.streak) ?? 0
        lastDay = try? c.decodeIfPresent(String.self, forKey: .lastDay)
        soundOn = (try? c.decodeIfPresent(Bool.self, forKey: .soundOn)) ?? true
        hapticsOn = (try? c.decodeIfPresent(Bool.self, forKey: .hapticsOn)) ?? true
        daily = try? c.decodeIfPresent(DailyRecord.self, forKey: .daily)
        let langRaw = (try? c.decodeIfPresent(String.self, forKey: .lang)) ?? "auto"
        lang = ["ja", "en"].contains(langRaw) ? langRaw : "auto"
        let ownedRaw = (try? c.decodeIfPresent([String].self, forKey: .owned)) ?? []
        owned = ownedRaw.filter { id in Skins.all.contains { $0.id == id } }
        if !owned.contains("neon") { owned.insert("neon", at: 0) }
        let skinRaw = (try? c.decodeIfPresent(String.self, forKey: .skin)) ?? "neon"
        skin = owned.contains(skinRaw) ? skinRaw : "neon"
        let missionsRaw = (try? c.decodeIfPresent([Mission].self, forKey: .missions)) ?? []
        missions = Array(missionsRaw.filter { $0.goal > 0 }.prefix(3))
    }
}

enum Meta {
    static let saveKey = "orbit-switch-save-v1"

    // MARK: dates

    /// "Y-M-D" in local time without zero padding (same format as the web version).
    static func today(_ date: Date = Date(), calendar: Calendar = .current) -> String {
        let c = calendar.dateComponents([.year, .month, .day], from: date)
        return "\(c.year ?? 0)-\(c.month ?? 0)-\(c.day ?? 0)"
    }

    static func dayDiff(_ a: String, _ b: String) -> Int? {
        func parse(_ s: String) -> Date? {
            let p = s.split(separator: "-").compactMap { Int($0) }
            guard p.count == 3 else { return nil }
            var utc = Calendar(identifier: .gregorian)
            utc.timeZone = TimeZone(identifier: "UTC")!
            return utc.date(from: DateComponents(year: p[0], month: p[1], day: p[2]))
        }
        guard let da = parse(a), let db = parse(b) else { return nil }
        return Int((db.timeIntervalSince(da) / 86400).rounded())
    }

    // MARK: persistence

    static func load(defaults: UserDefaults = .standard, rng: () -> Double = { Double.random(in: 0..<1) }) -> SaveData {
        var save = SaveData()
        if let data = defaults.data(forKey: saveKey), let decoded = try? JSONDecoder().decode(SaveData.self, from: data) {
            save = decoded
        }
        fillMissions(&save, rng: rng)
        return save
    }

    static func persist(_ save: SaveData, defaults: UserDefaults = .standard) {
        if let data = try? JSONEncoder().encode(save) { defaults.set(data, forKey: saveKey) }
    }

    // MARK: missions

    static func makeMission(_ save: SaveData, rng: () -> Double, exclude: [MissionKind]) -> Mission {
        let pool = MissionKind.allCases.filter { !exclude.contains($0) }
        let kind = pool[min(pool.count - 1, Int(rng() * Double(pool.count)))]
        let tier = min(kind.goals.count - 1, save.missionTier / 2)
        return Mission(kind: kind, goal: kind.goals[tier], progress: 0, reward: 10 + tier * 10)
    }

    static func fillMissions(_ save: inout SaveData, rng: () -> Double) {
        while save.missions.count < 3 {
            save.missions.append(makeMission(save, rng: rng, exclude: save.missions.map(\.kind)))
        }
    }

    // MARK: levels & coins

    /// Cumulative xp needed to reach level n+1 from level 1.
    static func xpForLevel(_ n: Int) -> Int { 40 * n * n + 10 * n }

    static func level(xp: Int) -> Int {
        var lvl = 1
        while xp >= xpForLevel(lvl) { lvl += 1 }
        return lvl
    }

    static func levelProgress(xp: Int) -> (level: Int, into: Int, need: Int) {
        let lvl = level(xp: xp)
        let prev = lvl == 1 ? 0 : xpForLevel(lvl - 1)
        return (lvl, xp - prev, xpForLevel(lvl) - prev)
    }

    /// √score based: good runs pay more, but one great run can't buy out the shop.
    static func runCoins(_ run: RunResult) -> Int {
        2 + Int(sqrt(Double(max(0, run.score))) * 1.2) + Int(sqrt(Double(max(0, run.gems))) * 2)
    }

    // MARK: daily bonus

    /// Returns the bonus coins granted now (0 if already claimed today).
    static func checkDaily(_ save: inout SaveData, now: Date = Date()) -> Int {
        let t = today(now)
        if save.lastDay == t { return 0 }
        let diff = save.lastDay.flatMap { dayDiff($0, t) } ?? 999
        save.streak = diff == 1 ? save.streak + 1 : 1
        save.lastDay = t
        let bonus = min(10 + (save.streak - 1) * 5, 50)
        save.coins += bonus
        return bonus
    }

    // MARK: runs

    static func applyRun(_ save: inout SaveData, _ run: RunResult, rng: () -> Double = { Double.random(in: 0..<1) }) -> RunSummary {
        var summary = RunSummary(prevBest: save.best)
        save.plays += 1
        save.totalGems += run.gems
        if run.score > save.best {
            save.best = run.score
            summary.newBest = summary.prevBest > 0
        }
        summary.coins += runCoins(run)

        let before = level(xp: save.xp)
        save.xp += run.score
        summary.levelUps = level(xp: save.xp) - before
        summary.coins += summary.levelUps * 10

        for i in save.missions.indices {
            let m = save.missions[i]
            let v = run.value(for: m.kind)
            save.missions[i].progress = m.kind.cumulative ? m.progress + v : max(m.progress, v)
            if save.missions[i].progress >= m.goal {
                summary.completed.append(save.missions[i])
                summary.coins += m.reward
            }
        }
        if !summary.completed.isEmpty {
            let done = Set(summary.completed.map(\.id))
            save.missions.removeAll { done.contains($0.id) }
            save.missionTier += summary.completed.count
            fillMissions(&save, rng: rng)
        }
        save.coins += summary.coins
        return summary
    }

    // MARK: shop

    /// Buys (or equips, if owned) a skin. Returns false if it can't be afforded.
    @discardableResult
    static func buySkin(_ save: inout SaveData, id: String) -> Bool {
        guard let skin = Skins.all.first(where: { $0.id == id }) else { return false }
        if save.owned.contains(id) {
            save.skin = id
            return true
        }
        guard save.coins >= skin.price else { return false }
        save.coins -= skin.price
        save.owned.append(id)
        save.skin = id
        return true
    }

    // MARK: daily challenge

    /// FNV-1a over UTF-16 code units: identical to the web version, so both share the same stage.
    static func dailySeed(_ day: String) -> UInt32 {
        var h: UInt32 = 2_166_136_261
        for u in day.utf16 { h = (h ^ UInt32(u)) &* 16_777_619 }
        return h
    }

    static func dailyBest(_ save: SaveData, day: String) -> Int {
        save.daily?.day == day ? save.daily!.best : 0
    }

    static func recordDaily(_ save: inout SaveData, day: String, score: Int) -> (prevBest: Int, best: Int, newBest: Bool) {
        if save.daily?.day != day { save.daily = DailyRecord(day: day, best: 0, tries: 0) }
        let prev = save.daily!.best
        save.daily!.tries += 1
        if score > prev { save.daily!.best = score }
        return (prev, save.daily!.best, prev > 0 && score > prev)
    }
}
