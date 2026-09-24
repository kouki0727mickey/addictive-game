// Owns the save data, the current run and the screen state. SwiftUI observes it;
// GameScene drives it every frame and renders it.

import Foundation
import SwiftUI

enum Screen { case menu, play, pause, over, shop, missions }
enum Mode { case normal, daily }

struct HUDState: Equatable {
    var score = 0
    var multText = ""
    var feverPct = 0.0
    var feverOn = false
    var bestText = ""
    var bestBeaten = false
}

struct OverInfo {
    var score = 0
    var isDaily = false
    var newBest = false
    var bestText = ""
    var tease = ""
    var details: [(String, String)] = []
    var coins = 0
    var unlockText = ""
    var completed: [Mission] = []
    var shareText = ""
}

final class GameModel: ObservableObject {
    @Published private(set) var screen: Screen = .menu
    @Published var save: SaveData
    @Published private(set) var hud = HUDState()
    @Published private(set) var over = OverInfo()
    @Published private(set) var dailyBonus = 0
    @Published var shopMessage = ""

    let haptics = Haptics()
    let sound = Sound()
    private(set) lazy var scene: GameScene = {
        let s = GameScene(size: CGSize(width: 390, height: 844))
        s.model = self
        s.scaleMode = .resizeFill
        return s
    }()

    /// The run being rendered: an attract-mode demo while in menus, the player's run otherwise.
    private(set) var game = GameState(seed: UInt32.random(in: 0...UInt32.max))
    private(set) var isDemo = true
    private(set) var mode: Mode = .normal
    private var runDay = ""
    private var runBest = 0
    private var retryLockUntil = Date.distantPast
    private var announcedMissions = Set<UUID>()

    // timers driven by the scene
    var deathTimer = 0.0
    var hitStop = 0.0
    var slowMo = 0.0
    var readyTimer = 0.0

    init() {
        save = Meta.load()
        applySettings()
        dailyBonus = Meta.checkDaily(&save)
        Meta.persist(save)
    }

    // MARK: settings

    private func applySettings() {
        sound.enabled = save.soundOn
        haptics.enabled = save.hapticsOn
    }

    func toggleSound() {
        save.soundOn.toggle()
        applySettings()
        Meta.persist(save)
    }

    func toggleHaptics() {
        save.hapticsOn.toggle()
        applySettings()
        Meta.persist(save)
        haptics.switchRing() // immediate feedback that it is on
    }

    /// An app left in the background for days should still pay the daily bonus.
    func becameActive() {
        let bonus = Meta.checkDaily(&save)
        if bonus > 0 {
            dailyBonus = bonus
            Meta.persist(save)
        }
    }

    // MARK: flow

    func show(_ s: Screen) {
        if s == .shop { shopMessage = "" }
        screen = s
    }

    func startGame(_ newMode: Mode? = nil) {
        if let newMode { mode = newMode }
        runDay = Meta.today()
        runBest = mode == .daily ? Meta.dailyBest(save, day: runDay) : save.best
        let seed = mode == .daily ? Meta.dailySeed(runDay) : UInt32.random(in: 0...UInt32.max)
        game = GameState(seed: seed)
        isDemo = false
        deathTimer = 0
        hitStop = 0
        slowMo = 0
        readyTimer = 0
        announcedMissions = []
        hud = HUDState()
        haptics.prepare()
        scene.resetRun()
        screen = .play
        updateHUD()
    }

    func retryIfAllowed() {
        guard Date() >= retryLockUntil else { return }
        startGame()
    }

    func startDemoIfNeeded() {
        if !isDemo || !game.alive {
            game = GameState(seed: UInt32.random(in: 0...UInt32.max))
            isDemo = true
            scene.resetRun()
        }
    }

    func tap() {
        guard screen == .play, readyTimer <= 0 else { return }
        game.switchRing()
    }

    func pause() {
        if screen == .play && game.alive && !isDemo { screen = .pause }
    }

    func resume() {
        guard screen == .pause else { return }
        readyTimer = 0.8 // re-orient before time moves
        screen = .play
    }

    var tutorialActive: Bool { save.plays < 3 && game.passedSpikes < 4 }

    // MARK: events (sound + haptics; visuals live in GameScene)

    func handle(_ e: GameEvent) {
        switch e {
        case .switched:
            sound.switchRing()
            haptics.switchRing()
        case let .gem(_, _, combo, _):
            sound.gem(combo: combo)
            haptics.gem()
        case .nearMiss:
            sound.nearMiss()
            haptics.nearMiss()
            slowMo = 0.12
        case .smash:
            sound.smash()
            haptics.smash()
        case .fever:
            sound.fever()
            haptics.fever()
        case .feverEnd, .comboLost:
            break
        case .death:
            sound.death()
            haptics.death()
            deathTimer = 0.9
            hitStop = 0.12
        }
    }

    // MARK: HUD

    /// Returns the text of a mission completed this frame, if any (shown as a popup by the scene).
    func checkMissionsLive() -> String? {
        for m in save.missions where !m.kind.cumulative && !announcedMissions.contains(m.id) {
            let v: Int
            switch m.kind {
            case .score: v = game.score
            case .gems: v = game.gems
            case .nearMisses: v = game.nearMisses
            case .bestCombo: v = game.bestCombo
            case .feverCount: v = game.feverCount
            case .plays: v = 0
            }
            if v >= m.goal {
                announcedMissions.insert(m.id)
                sound.coin()
                return "✅ " + m.text
            }
        }
        return nil
    }

    /// Updates the published HUD only when something changed. Returns true the moment the best is beaten.
    @discardableResult
    func updateHUD() -> Bool {
        var h = HUDState()
        h.score = game.score
        let m = game.effectiveMultiplier
        h.multText = m > 1 ? "×\(m)" + (game.fever > 0 ? " FEVER" : "") : (game.combo >= 2 ? "\(game.combo) combo" : "")
        h.feverOn = game.fever > 0
        let pct = h.feverOn ? game.fever / GameConfig.feverDuration : Double(game.combo % GameConfig.feverEvery) / Double(GameConfig.feverEvery)
        h.feverPct = (pct * 50).rounded() / 50
        h.bestBeaten = runBest > 0 && game.score > runBest
        h.bestText = runBest == 0 ? "" : h.bestBeaten ? "NEW BEST!" : (mode == .daily ? "📅 BEST \(runBest)" : "BEST \(runBest)")
        let justBeaten = h.bestBeaten && !hud.bestBeaten && runBest > 0
        if h != hud { hud = h }
        if justBeaten {
            sound.coin()
            haptics.celebrate()
        }
        return justBeaten
    }

    // MARK: end of run

    func endGame() {
        let run = RunResult(score: game.score, gems: game.gems, nearMisses: game.nearMisses, bestCombo: game.bestCombo, feverCount: game.feverCount)
        let sum = Meta.applyRun(&save, run)
        var prevBest = sum.prevBest
        var best = save.best
        var newBest = sum.newBest
        var bestSuffix = ""
        if mode == .daily {
            let rec = Meta.recordDaily(&save, day: runDay, score: run.score)
            prevBest = rec.prevBest
            best = rec.best
            newBest = rec.newBest
            bestSuffix = "（\(save.daily?.tries ?? 1)回目）"
        }
        Meta.persist(save)

        var o = OverInfo()
        o.score = run.score
        o.isDaily = mode == .daily
        o.newBest = newBest
        o.bestText = "\(best)" + bestSuffix
        let gap = best - run.score
        if newBest { o.tease = "記録更新！ +\(run.score - prevBest)" }
        else if best == 0 { o.tease = "トゲをよけると1点！ タップで内⇄外を切替" }
        else if prevBest == 0 && run.score > 0 { o.tease = "初記録！ 次はこれを超えよう" }
        else if gap == 0 { o.tease = "ベストに並んだ！ あと1点で更新！" }
        else if gap <= 5 { o.tease = "おしい！ あと\(gap + 1)点でベスト更新！" }
        else { o.tease = "ベストまで あと\(gap + 1)点" }
        o.details = [("ジェム", "\(run.gems)"), ("最大コンボ", "\(run.bestCombo)"), ("ニアミス", "\(run.nearMisses)")]
        if game.smashed > 0 { o.details.append(("粉砕", "\(game.smashed)")) }
        if sum.levelUps > 0 { o.details.append(("レベルアップ!", "Lv\(Meta.level(xp: save.xp))")) }
        o.coins = sum.coins
        if let next = Skins.all.filter({ !save.owned.contains($0.id) }).min(by: { $0.price < $1.price }) {
            o.unlockText = save.coins >= next.price ? "🔓 スキン「\(next.name)」を解放できます！" : "次のスキン「\(next.name)」まで 🪙\(next.price - save.coins)"
        }
        o.completed = sum.completed
        o.shareText = mode == .daily
            ? "ORBIT SWITCH 今日のチャレンジ（\(runDay)）で \(run.score)点！ 同じステージで勝負しよう #ORBITSWITCH"
            : "ORBIT SWITCH で \(run.score)点！（ベスト \(save.best)）タップだけの中毒ゲーム #ORBITSWITCH"
        over = o
        screen = .over
        retryLockUntil = Date().addingTimeInterval(0.6) // a panic-tap at death must not skip the results

        if newBest {
            sound.best()
            haptics.celebrate()
        } else if !sum.completed.isEmpty || sum.levelUps > 0 {
            sound.coin()
            haptics.celebrate()
        }
    }

    // MARK: shop

    func tapSkin(_ skin: Skin) {
        if Meta.buySkin(&save, id: skin.id) {
            sound.coin()
            haptics.celebrate()
            shopMessage = ""
            Meta.persist(save)
        } else {
            haptics.denied()
            shopMessage = "コインが足りません（あと 🪙\(skin.price - save.coins)）— プレイして集めよう！"
        }
    }

    var canBuySomething: Bool {
        Skins.all.contains { !save.owned.contains($0.id) && save.coins >= $0.price }
    }
}
