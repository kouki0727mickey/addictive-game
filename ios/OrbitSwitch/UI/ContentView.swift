// SwiftUI screens layered over the SpriteKit scene.

import SpriteKit
import SwiftUI

extension Color {
    init(hex: UInt32, opacity: Double = 1) {
        self.init(red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255, blue: Double(hex & 0xFF) / 255, opacity: opacity)
    }

    static let fg = Color(hex: 0xEEF2FF)
    static let muted = Color(hex: 0x8A90B8)
    static let accent = Color(hex: 0x4DF3FF)
    static let gold = Color(hex: 0xFFC94D)
    static let danger = Color(hex: 0xFF4D6D)
    static let panel = Color(hex: 0x101230, opacity: 0.85)
}

struct ContentView: View {
    @EnvironmentObject var model: GameModel
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ZStack {
            SpriteView(scene: model.scene, options: [.ignoresSiblingOrder])
                .ignoresSafeArea()

            switch model.screen {
            case .play: HUDView().allowsHitTesting(false)
            case .pause: PauseView()
            case .menu: MenuView()
            case .over: OverView()
            case .shop: ShopView()
            case .missions: MissionsView()
            }
        }
        .foregroundStyle(Color.fg)
        .onChange(of: scenePhase) { phase in
            if phase == .active { model.becameActive() } else { model.pause() }
        }
    }
}

// MARK: - common pieces

struct Dim: View {
    var body: some View {
        RadialGradient(colors: [Color(hex: 0x07071A, opacity: 0.35), Color(hex: 0x07071A, opacity: 0.88)], center: .center, startRadius: 0, endRadius: 600)
            .ignoresSafeArea()
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 20, weight: .heavy, design: .rounded))
            .padding(.vertical, 16)
            .padding(.horizontal, 32)
            .background(LinearGradient(colors: [Color(hex: 0x1BD4FF), Color(hex: 0x7A5CFF)], startPoint: .topLeading, endPoint: .bottomTrailing))
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .shadow(color: Color.accent.opacity(0.35), radius: 14, y: 6)
            .scaleEffect(configuration.isPressed ? 0.96 : 1)
    }
}

struct PanelButtonStyle: ButtonStyle {
    var border = Color.white.opacity(0.15)
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 16, weight: .bold, design: .rounded))
            .padding(.vertical, 12)
            .padding(.horizontal, 18)
            .background(Color.panel)
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(border, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .scaleEffect(configuration.isPressed ? 0.96 : 1)
    }
}

struct ProgressBar: View {
    var value: Double
    var colors: [Color]
    var height: CGFloat = 6
    var body: some View {
        GeometryReader { g in
            ZStack(alignment: .leading) {
                Capsule().fill(Color.white.opacity(0.1))
                Capsule().fill(LinearGradient(colors: colors, startPoint: .leading, endPoint: .trailing))
                    .frame(width: g.size.width * CGFloat(min(1, max(0, value))))
            }
        }
        .frame(height: height)
    }
}

struct MissionRow: View {
    let mission: Mission
    var done = false
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text((done ? "✅ " : "") + mission.text)
                Text("(\(min(mission.progress, mission.goal))/\(mission.goal))").font(.caption).foregroundStyle(Color.muted)
                Spacer()
                Text("🪙\(mission.reward)").foregroundStyle(Color.gold)
            }
            .font(.system(size: 14, weight: .semibold))
            ProgressBar(value: Double(mission.progress) / Double(mission.goal), colors: [.gold, .gold], height: 4)
        }
        .padding(10)
        .background(Color.panel)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(done ? Color.gold : .clear, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

// MARK: - HUD

struct HUDView: View {
    @EnvironmentObject var model: GameModel
    var body: some View {
        let h = model.hud
        VStack(spacing: 2) {
            Text(h.bestText)
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(h.bestBeaten ? Color.gold : Color.muted)
                .frame(height: 16)
            Text("\(h.score)")
                .font(.system(size: 56, weight: .heavy, design: .rounded))
                .monospacedDigit()
                .shadow(color: Color.accent.opacity(0.6), radius: 12)
            Text(h.multText)
                .font(.system(size: 18, weight: .bold, design: .rounded))
                .foregroundStyle(Color.gold)
                .frame(height: 22)
            ProgressBar(value: h.feverPct, colors: h.feverOn ? [Color(hex: 0xFF7AD9), Color(hex: 0xFF7AD9)] : [.gold, Color(hex: 0xFF7AD9)], height: 5)
                .frame(width: 120)
                .animation(.linear(duration: 0.15), value: h.feverPct)
            Spacer()
        }
        .padding(.top, 8)
    }
}

// MARK: - Pause

struct PauseView: View {
    @EnvironmentObject var model: GameModel
    var body: some View {
        ZStack {
            Dim()
            VStack(spacing: 16) {
                Text(L10n.t("pause.title")).font(.system(size: 28, weight: .heavy, design: .rounded))
                Button(L10n.t("pause.resume")) { model.resume() }.buttonStyle(PrimaryButtonStyle())
            }
        }
        .contentShape(Rectangle())
        .onTapGesture { model.resume() }
    }
}

// MARK: - Menu

struct MenuView: View {
    @EnvironmentObject var model: GameModel
    var body: some View {
        let lp = Meta.levelProgress(xp: model.save.xp)
        let dailyBest = Meta.dailyBest(model.save, day: Meta.today())
        ZStack {
            Dim().onTapGesture { model.startGame(.normal) }
            VStack(spacing: 14) {
                VStack(spacing: 0) {
                    Text("ORBIT").font(.system(size: 60, weight: .black, design: .rounded))
                    Text("SWITCH").font(.system(size: 60, weight: .black, design: .rounded)).foregroundStyle(Color.accent)
                }
                .shadow(color: Color.accent.opacity(0.7), radius: 18)
                Text(L10n.t("menu.taglineApp"))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Color.muted)
                HStack(spacing: 18) {
                    Text("BEST **\(model.save.best)**")
                    Text("🪙 **\(model.save.coins)**")
                    Text("Lv **\(lp.level)**")
                }
                .font(.system(size: 18, design: .rounded))
                ProgressBar(value: Double(lp.into) / Double(lp.need), colors: [.accent, Color(hex: 0xB28CFF)]).frame(width: 240)
                if model.dailyBonus > 0 {
                    Text(L10n.t("menu.dailyBonus", ["bonus": model.dailyBonus, "streak": model.save.streak]))
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color.gold)
                        .padding(.vertical, 8).padding(.horizontal, 14)
                        .background(Color.panel)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.gold, lineWidth: 1))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                Button(L10n.t("menu.play")) { model.startGame(.normal) }.buttonStyle(PrimaryButtonStyle())
                Button {
                    model.startGame(.daily)
                } label: {
                    HStack {
                        Text(L10n.t("menu.daily"))
                        Text(dailyBest > 0 ? "BEST \(dailyBest)" : L10n.t("menu.new")).font(.caption.bold()).foregroundStyle(Color.gold)
                    }
                }
                .buttonStyle(PanelButtonStyle(border: Color.gold.opacity(0.5)))
                HStack(spacing: 10) {
                    Button(L10n.t("menu.skins")) { model.show(.shop) }
                        .buttonStyle(PanelButtonStyle())
                        .overlay(alignment: .topTrailing) {
                            if model.canBuySomething {
                                Circle().fill(Color.danger).frame(width: 12, height: 12).offset(x: 4, y: -4)
                            }
                        }
                    Button(L10n.t("menu.missions")) { model.show(.missions) }.buttonStyle(PanelButtonStyle())
                    Button(model.save.soundOn ? "🔊" : "🔇") { model.toggleSound() }
                        .buttonStyle(PanelButtonStyle())
                        .accessibilityLabel(L10n.t("menu.sound"))
                    Button(model.save.hapticsOn ? "📳" : "📴") { model.toggleHaptics() }
                        .buttonStyle(PanelButtonStyle())
                        .accessibilityLabel(L10n.t("menu.haptics"))
                    Button(L10n.lang == "ja" ? "EN" : "JA") { model.toggleLanguage() }
                        .buttonStyle(PanelButtonStyle())
                        .accessibilityLabel(L10n.t("menu.lang"))
                }
            }
            .padding(16)
        }
    }
}

// MARK: - Game over

struct OverView: View {
    @EnvironmentObject var model: GameModel
    @State private var shownCoins = 0

    var body: some View {
        let o = model.over
        ZStack {
            Dim().onTapGesture { model.retryIfAllowed() }
            ScrollView {
                VStack(spacing: 12) {
                    if o.isDaily { Text(L10n.t("over.daily")).bold().foregroundStyle(Color.gold) }
                    if o.newBest {
                        Text("NEW BEST!").font(.system(size: 28, weight: .black, design: .rounded)).foregroundStyle(Color.gold)
                    }
                    Text("\(o.score)").font(.system(size: 96, weight: .black, design: .rounded)).monospacedDigit()
                    Text("BEST **\(o.bestText)**").foregroundStyle(Color.muted)
                    Text(o.tease).bold().foregroundStyle(Color.accent).multilineTextAlignment(.center)
                    HStack(spacing: 14) {
                        ForEach(o.details.indices, id: \.self) { i in
                            Text("\(o.details[i].0) **\(o.details[i].1)**")
                        }
                        Text("🪙 **+\(shownCoins)**")
                    }
                    .font(.system(size: 14))
                    .foregroundStyle(Color.muted)
                    if !o.unlockText.isEmpty { Text(o.unlockText).font(.system(size: 14, weight: .bold)).foregroundStyle(Color.gold) }
                    VStack(spacing: 8) {
                        ForEach(o.completed) { MissionRow(mission: $0, done: true) }
                        ForEach(model.save.missions) { MissionRow(mission: $0) }
                    }
                    .frame(maxWidth: 380)
                    HStack(spacing: 10) {
                        Button(L10n.t("over.menu")) { model.show(.menu) }.buttonStyle(PanelButtonStyle())
                        ShareLink(item: o.shareText) { Text("📤") }
                            .buttonStyle(PanelButtonStyle())
                            .accessibilityLabel(L10n.t("over.share"))
                        Button(L10n.t("over.retry")) { model.retryIfAllowed() }.buttonStyle(PrimaryButtonStyle())
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 40)
                .frame(maxWidth: .infinity)
            }
        }
        .onAppear { countUp(to: o.coins) }
    }

    // Rewards feel bigger when you watch them tick up.
    private func countUp(to target: Int) {
        shownCoins = 0
        let steps = 20
        for i in 1...steps {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 0.035) {
                let k = Double(i) / Double(steps)
                shownCoins = Int((Double(target) * (1 - pow(1 - k, 3))).rounded())
            }
        }
    }
}

// MARK: - Shop

struct ShopView: View {
    @EnvironmentObject var model: GameModel
    var body: some View {
        ZStack {
            Dim()
            VStack(spacing: 14) {
                Text(L10n.t("shop.title")).font(.system(size: 28, weight: .heavy, design: .rounded))
                Text("🪙 **\(model.save.coins)**").font(.system(size: 20))
                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 3), spacing: 10) {
                    ForEach(Skins.all) { skin in
                        SkinCell(skin: skin)
                    }
                }
                .frame(maxWidth: 380)
                Text(model.shopMessage).font(.footnote).foregroundStyle(Color.muted).multilineTextAlignment(.center)
                Button(L10n.t("back")) { model.show(.menu) }.buttonStyle(PanelButtonStyle())
            }
            .padding(16)
        }
    }
}

struct SkinCell: View {
    @EnvironmentObject var model: GameModel
    let skin: Skin
    var body: some View {
        let owned = model.save.owned.contains(skin.id)
        let selected = model.save.skin == skin.id
        let affordable = !owned && model.save.coins >= skin.price
        Button {
            model.tapSkin(skin)
        } label: {
            VStack(spacing: 6) {
                Group {
                    if let hex = skin.color {
                        Circle().fill(Color(hex: hex))
                    } else {
                        Circle().fill(AngularGradient(colors: [.red, .orange, .yellow, .green, .cyan, .blue, .purple, .red], center: .center))
                    }
                }
                .frame(width: 28, height: 28)
                Text(skin.name).font(.system(size: 13, weight: .semibold))
                Text(owned ? L10n.t(selected ? "shop.equipped" : "shop.owned") : (affordable ? L10n.t("shop.buy") + " " : "") + "🪙\(skin.price)")
                    .font(.system(size: 11, weight: affordable ? .bold : .regular))
                    .foregroundStyle(affordable ? Color.gold : Color.muted)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Color.panel)
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(selected ? Color.accent : affordable ? Color.gold : .clear, lineWidth: 2))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .opacity(owned || affordable ? 1 : 0.7)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

// MARK: - Missions

struct MissionsView: View {
    @EnvironmentObject var model: GameModel
    var body: some View {
        ZStack {
            Dim()
            VStack(spacing: 14) {
                Text(L10n.t("missions.title")).font(.system(size: 28, weight: .heavy, design: .rounded))
                VStack(spacing: 8) {
                    ForEach(model.save.missions) { MissionRow(mission: $0) }
                }
                .frame(maxWidth: 380)
                Text(L10n.t("missions.lifetime", ["plays": model.save.plays, "gems": model.save.totalGems, "level": Meta.level(xp: model.save.xp)]))
                    .font(.footnote)
                    .foregroundStyle(Color.muted)
                Button(L10n.t("back")) { model.show(.menu) }.buttonStyle(PanelButtonStyle())
            }
            .padding(16)
        }
    }
}
