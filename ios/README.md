# ORBIT SWITCH — iOS 版（Swift + SpriteKit）

Web 版（`../js`）をネイティブの iPhone / iPad アプリに移植したものです。

- **振動:** iPhone の Taptic Engine（`UIImpactFeedbackGenerator` / `UINotificationFeedbackGenerator`）を直接使用
  - リング切替：軽いタップ ／ ジェム：柔らかいタップ ／ ニアミス：硬いタップ ／ 粉砕：重いタップ
  - FEVER・記録更新：成功パターン ／ 死亡：重い衝撃 → エラーパターン
  - メニューの 📳 ボタンで音とは別にオン/オフ可能（iPad には振動モーターがないため無効）
- **効果音:** 起動時に合成した PCM を AVAudioEngine で再生（音声ファイルなし、消音スイッチに従う）
- **言語:** 日本語 / 英語。端末の言語（iOS の「設定 → ORBIT SWITCH → 言語」も含む）に従い、メニューの EN / JA ボタンでも切替可能。文言は `js/i18n.js` から `npm run gen:ios` で `Core/Strings.generated.swift` を生成（Web 版と共通）
- **ゲームロジック:** `Core/GameCore.swift` は Web 版と同じ乱数・同じ生成規則。**今日のチャレンジは Web 版と同じステージ**になります（テストで一致を検証）

## 構成

| パス | 役割 |
|------|------|
| `OrbitSwitch/Core/GameCore.swift` | シミュレーション（UIKit 非依存・決定的） |
| `OrbitSwitch/Core/Meta.swift` | コイン・スキン・ミッション・レベル・デイリー・セーブ（壊れたセーブにも耐える） |
| `OrbitSwitch/Game/GameScene.swift` | SpriteKit 描画・タップ入力・演出 |
| `OrbitSwitch/Game/GameModel.swift` | 画面遷移・スコア・結果画面 |
| `OrbitSwitch/Game/Haptics.swift` / `Sound.swift` | 振動・効果音 |
| `OrbitSwitch/UI/ContentView.swift` | SwiftUI のメニュー・HUD・結果・スキン・ミッション画面 |
| `OrbitSwitchTests/` | XCTest（Web 版との一致・公平性・経済バランスなど） |
| `project.yml` | XcodeGen 定義（`.xcodeproj` はここから生成） |

## ビルド

Mac がある場合:

```sh
brew install xcodegen
cd ios && xcodegen generate
open OrbitSwitch.xcodeproj
```

Mac がなくても、push するたびに GitHub Actions（`.github/workflows/ios.yml`）が macOS 上でビルドとテストを実行します。
