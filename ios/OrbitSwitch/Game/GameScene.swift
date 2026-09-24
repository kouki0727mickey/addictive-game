// Renders GameModel.game with SpriteKit and drives the simulation every frame.

import SpriteKit
import UIKit

extension UIColor {
    convenience init(hex: UInt32, alpha: CGFloat = 1) {
        self.init(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255, blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
    }
}

enum Palette {
    static let bg = UIColor(hex: 0x07071A)
    static let bgFever = UIColor(hex: 0x1E0930)
    static let ring = UIColor(hex: 0x788CFF, alpha: 0.4)
    static let ringFever = UIColor(hex: 0xFF7AD9, alpha: 0.6)
    static let spike = UIColor(hex: 0xFF4D6D)
    static let spikeFever = UIColor(hex: 0xFF9EC0)
    static let gem = UIColor(hex: 0xFFC94D)
    static let accent = UIColor(hex: 0x4DF3FF)
    static let pink = UIColor(hex: 0xFF7AD9)
    static let muted = UIColor(hex: 0x8A90B8)
}

final class GameScene: SKScene {
    weak var model: GameModel?

    /// Space reserved at the top for the SwiftUI score HUD.
    static let hudHeight: CGFloat = 150

    private let world = SKNode() // shaken as a whole
    private let objectLayer = SKNode()
    private let effectLayer = SKNode()
    private var rings: [SKShapeNode] = []
    private let core = SKShapeNode(circleOfRadius: 1)
    private let player = SKShapeNode(circleOfRadius: 1)
    private let playerGlow = SKShapeNode(circleOfRadius: 1)
    private let trailNode = SKShapeNode()
    private let hintLabel = SKLabelNode(fontNamed: "HiraginoSans-W7")
    private var objectNodes: [Int: SKNode] = [:]
    private var trail: [(p: CGPoint, t: Double)] = []

    private var unit: CGFloat = 300
    private var center = CGPoint.zero
    private var lastTime: TimeInterval = 0
    private var shake: CGFloat = 0
    private var hue: CGFloat = 0
    private var layoutSize = CGSize.zero

    override func didMove(to view: SKView) {
        backgroundColor = Palette.bg
        view.isMultipleTouchEnabled = true
        addChild(world)
        world.addChild(core)
        world.addChild(objectLayer)
        world.addChild(trailNode)
        world.addChild(playerGlow)
        world.addChild(player)
        world.addChild(effectLayer)
        trailNode.lineCap = .round
        trailNode.lineJoin = .round
        player.lineWidth = 0
        playerGlow.lineWidth = 0
        playerGlow.alpha = 0.3
        hintLabel.fontSize = 28
        hintLabel.verticalAlignmentMode = .center
        hintLabel.numberOfLines = 2
        hintLabel.zPosition = 10
        addChild(hintLabel)
        layout()
    }

    override func didChangeSize(_ oldSize: CGSize) {
        super.didChangeSize(oldSize)
        if world.parent != nil { layout() }
    }

    // The outer ring plus player needs ~0.9 units of diameter: fit it below the HUD.
    private func layout() {
        guard size != layoutSize, size.width > 0 else { return }
        layoutSize = size
        let top = GameScene.hudHeight
        let bottom: CGFloat = 40
        let availH = size.height - top - bottom
        unit = min(size.width / 0.95, availH / 0.9, min(size.width, size.height))
        center = CGPoint(x: size.width / 2, y: bottom + availH / 2)

        rings.forEach { $0.removeFromParent() }
        rings = GameConfig.ringRadius.map { r in
            let n = SKShapeNode(circleOfRadius: CGFloat(r) * unit)
            n.position = center
            n.fillColor = .clear
            n.lineWidth = 2
            n.strokeColor = Palette.ring
            world.insertChild(n, at: 0)
            return n
        }
        core.position = center
        core.setScale(0.07 * unit)
        core.lineWidth = 0
        core.fillColor = Palette.accent.withAlphaComponent(0.12)
        player.setScale(CGFloat(GameConfig.playerRadius) * unit)
        playerGlow.setScale(CGFloat(GameConfig.playerRadius) * unit * 1.9)
        hintLabel.position = center
        // Object nodes are sized in points: rebuild them at the new scale.
        objectNodes.values.forEach { $0.removeFromParent() }
        objectNodes.removeAll()
    }

    /// World units (y up in the simulation, clockwise on screen) to scene points.
    private func toScene(_ x: Double, _ y: Double) -> CGPoint {
        CGPoint(x: center.x + CGFloat(x) * unit, y: center.y - CGFloat(y) * unit)
    }

    func resetRun() {
        objectNodes.values.forEach { $0.removeFromParent() }
        objectNodes.removeAll()
        effectLayer.removeAllChildren()
        trail.removeAll()
        shake = 0
    }

    // MARK: input

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        for _ in touches { model?.tap() }
    }

    // MARK: frame

    override func update(_ currentTime: TimeInterval) {
        let dt = lastTime == 0 ? 1.0 / 60 : min(0.05, currentTime - lastTime)
        lastTime = currentTime
        hue = (hue + CGFloat(dt) * 0.33).truncatingRemainder(dividingBy: 1)
        guard let model else { return }
        let game = model.game

        switch model.screen {
        case .menu, .shop, .missions:
            model.startDemoIfNeeded()
            let demo = model.game
            if demo.autopilotWantsSwitch() { demo.switchRing() }
            demo.step(dt)
            _ = demo.drainEvents()
        case .play:
            if model.readyTimer > 0 {
                model.readyTimer -= dt
            } else if model.hitStop > 0 {
                model.hitStop -= dt
            } else if game.alive {
                var scale = 1.0
                if model.slowMo > 0 {
                    model.slowMo -= dt
                    scale = 0.45
                }
                game.step(dt * scale)
            } else {
                model.deathTimer -= dt
                if model.deathTimer <= 0 { model.endGame() }
            }
            for e in game.drainEvents() {
                model.handle(e)
                effects(for: e)
            }
            if model.updateHUD() { popText(0, -0.08, "NEW BEST!", Palette.gem, 30) }
            if let text = model.checkMissionsLive() { popText(0, 0.1, text, Palette.gem, 17) }
        case .pause, .over:
            break
        }
        render(dt)
    }

    // MARK: effects

    private func effects(for e: GameEvent) {
        switch e {
        case let .gem(x, y, _, points):
            burst(x, y, Palette.gem, 10, 0.35)
            popText(x, y, "+\(points)", Palette.gem, 22)
        case let .nearMiss(x, y):
            popText(x, y, "CLOSE!", Palette.accent, 20)
        case let .smash(x, y):
            shake = max(shake, 6)
            burst(x, y, Palette.spike, 14, 0.5)
        case .fever:
            flash(0.35)
            popText(0, 0, "FEVER!!", Palette.pink, 44)
        case .feverEnd:
            popText(0, 0, "FEVER END", Palette.pink, 24)
        case let .comboLost(combo):
            if combo >= 3 { popText(0, 0.06, "combo lost", Palette.muted, 18) }
        case let .death(x, y):
            shake = 16
            flash(0.45)
            burst(x, y, skinColor(trail: false), 40, 0.7)
        case .switched:
            break
        }
    }

    private var reduceMotion: Bool { UIAccessibility.isReduceMotionEnabled }

    private func burst(_ x: Double, _ y: Double, _ color: UIColor, _ n: Int, _ speed: Double) {
        let origin = toScene(x, y)
        for _ in 0..<n {
            let a = Double.random(in: 0..<(2 * .pi))
            let v = (0.2 + Double.random(in: 0..<1)) * speed * Double(unit) * 0.35
            let p = SKShapeNode(rectOf: CGSize(width: 4, height: 4))
            p.fillColor = color
            p.lineWidth = 0
            p.position = origin
            effectLayer.addChild(p)
            let life = 0.6 + Double.random(in: 0..<0.4)
            let move = SKAction.moveBy(x: CGFloat(cos(a) * v), y: CGFloat(sin(a) * v), duration: life)
            move.timingMode = .easeOut
            p.run(.sequence([.group([move, .fadeOut(withDuration: life)]), .removeFromParent()]))
        }
    }

    private func popText(_ x: Double, _ y: Double, _ text: String, _ color: UIColor, _ size: CGFloat) {
        let l = SKLabelNode(fontNamed: "HiraginoSans-W7")
        l.text = text
        l.fontSize = size
        l.fontColor = color
        l.verticalAlignmentMode = .center
        var p = toScene(x, y)
        // keep the whole label on screen
        let half = l.frame.width / 2 + 8
        p.x = min(self.size.width - half, max(half, p.x))
        p.y = min(self.size.height - size, max(size, p.y))
        l.position = p
        l.zPosition = 20
        effectLayer.addChild(l)
        let rise = SKAction.moveBy(x: 0, y: CGFloat(0.08) * unit, duration: 0.9)
        l.run(.sequence([.group([rise, .sequence([.wait(forDuration: 0.45), .fadeOut(withDuration: 0.45)])]), .removeFromParent()]))
    }

    private func flash(_ strength: CGFloat) {
        guard !reduceMotion else { return }
        let f = SKSpriteNode(color: .white, size: size)
        f.anchorPoint = .zero
        f.alpha = strength
        f.zPosition = 50
        addChild(f)
        f.run(.sequence([.fadeOut(withDuration: 0.3), .removeFromParent()]))
    }

    // MARK: render

    private func skinColor(trail: Bool) -> UIColor {
        guard let model else { return Palette.accent }
        let skin = Skins.find(model.save.skin)
        guard let hex = trail ? skin.trail : skin.color else {
            return UIColor(hue: hue, saturation: 1, brightness: 1, alpha: 1)
        }
        return UIColor(hex: hex)
    }

    private func makeSpike() -> SKShapeNode {
        let r = CGFloat(GameConfig.spikeRadius) * unit
        let path = CGMutablePath()
        for i in 0..<8 {
            let a = CGFloat(i) / 8 * 2 * .pi
            let rr = i % 2 == 1 ? r * 0.55 : r * 1.25
            let pt = CGPoint(x: cos(a) * rr, y: sin(a) * rr)
            if i == 0 { path.move(to: pt) } else { path.addLine(to: pt) }
        }
        path.closeSubpath()
        let n = SKShapeNode(path: path)
        n.lineWidth = 0
        n.fillColor = Palette.spike
        let glow = SKShapeNode(circleOfRadius: r * 1.5)
        glow.lineWidth = 0
        glow.fillColor = Palette.spike.withAlphaComponent(0.18)
        glow.zPosition = -1
        n.addChild(glow)
        return n
    }

    private func makeGem() -> SKShapeNode {
        let r = CGFloat(GameConfig.gemRadius) * unit
        let n = SKShapeNode(rectOf: CGSize(width: r * 1.4, height: r * 1.4))
        n.zRotation = .pi / 4
        n.lineWidth = 0
        n.fillColor = Palette.gem
        let glow = SKShapeNode(circleOfRadius: r * 1.4)
        glow.lineWidth = 0
        glow.fillColor = Palette.gem.withAlphaComponent(0.2)
        glow.zPosition = -1
        n.addChild(glow)
        return n
    }

    private func render(_ dt: Double) {
        guard let model else { return }
        layout()
        let game = model.game
        let demo = model.screen == .menu || model.screen == .shop || model.screen == .missions
        let fever = game.fever > 0

        backgroundColor = fever ? Palette.bgFever : Palette.bg
        let tNow = CACurrentMediaTime()
        for (i, ring) in rings.enumerated() {
            ring.strokeColor = fever ? Palette.ringFever : Palette.ring
            ring.lineWidth = 2 + CGFloat(sin(tNow * 4 + Double(i))) * 0.8
        }

        // screen shake
        if reduceMotion { shake = 0 }
        if shake > 0 {
            world.position = CGPoint(x: CGFloat.random(in: -0.5...0.5) * shake, y: CGFloat.random(in: -0.5...0.5) * shake)
            shake = max(0, shake - CGFloat(dt) * 40)
        } else {
            world.position = .zero
        }

        // objects: create new nodes, move them, drop nodes whose object is gone
        objectLayer.alpha = demo ? 0.35 : 1
        var alive = Set<Int>()
        for o in game.objects {
            alive.insert(o.id)
            let node: SKNode
            if let existing = objectNodes[o.id] {
                node = existing
            } else {
                node = o.kind == .spike ? makeSpike() : makeGem()
                objectLayer.addChild(node)
                objectNodes[o.id] = node
            }
            let q = GameState.position(of: o)
            node.position = toScene(q.x, q.y)
            if o.kind == .spike, let s = node as? SKShapeNode {
                s.zRotation = -CGFloat(o.angle)
                s.fillColor = fever ? Palette.spikeFever : Palette.spike
            } else {
                node.setScale(1 + CGFloat(sin(tNow * 8)) * 0.12)
            }
        }
        for (id, node) in objectNodes where !alive.contains(id) {
            node.removeFromParent()
            objectNodes[id] = nil
        }

        // player + trail
        let showPlayer = game.alive && model.screen != .over
        // blink while invulnerable after fever / in the last second of fever
        let warn = game.grace > 0 || (game.fever > 0 && game.fever < 1)
        let blinkOff = warn && Int(game.t * 14) % 2 == 0
        let pp = game.playerPos
        let pos = toScene(pp.x, pp.y)
        player.isHidden = !showPlayer || blinkOff
        playerGlow.isHidden = player.isHidden
        trailNode.isHidden = !showPlayer
        player.position = pos
        playerGlow.position = pos
        let color = skinColor(trail: false)
        player.fillColor = fever ? .white : color
        playerGlow.fillColor = color
        player.alpha = demo ? 0.35 : 1
        playerGlow.alpha = demo ? 0.1 : 0.3

        if showPlayer {
            if trail.last?.t != game.t { trail.append((pos, game.t)) }
            while let first = trail.first, game.t - first.t > 0.2 { trail.removeFirst() }
            let path = CGMutablePath()
            for (i, tp) in trail.enumerated() {
                if i == 0 { path.move(to: tp.p) } else { path.addLine(to: tp.p) }
            }
            trailNode.path = path
            trailNode.strokeColor = skinColor(trail: true).withAlphaComponent(demo ? 0.15 : 0.45)
            trailNode.lineWidth = CGFloat(GameConfig.playerRadius) * unit * 1.5
        }

        // hints: tutorial "TAP!" on the first runs, READY after resuming
        hintLabel.isHidden = true
        if model.screen == .play && game.alive {
            if model.readyTimer > 0 {
                showHint("READY", size: 30)
            } else if model.tutorialActive {
                var cur = Double.infinity
                var other = Double.infinity
                for o in game.objects where o.kind == .spike {
                    let rel = o.angle - game.angle
                    if rel < 0 { continue }
                    if o.ring == game.ring { cur = min(cur, rel) } else { other = min(other, rel) }
                }
                if cur < 0.9 && other > cur + 0.15 {
                    showHint("TAP!", size: 26 + CGFloat(sin(tNow * 18)) * 3)
                } else if game.passedSpikes == 0 {
                    showHint(L10n.t("hint.start"), size: 15)
                }
            }
        }
    }

    private func showHint(_ text: String, size: CGFloat) {
        hintLabel.isHidden = false
        hintLabel.text = text
        hintLabel.fontSize = size
        hintLabel.fontColor = .white
    }
}
