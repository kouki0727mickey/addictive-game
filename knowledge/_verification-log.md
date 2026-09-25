# 事実確認ログ

記事中の事実記述をいつ・どう確認したかの記録。鮮度管理と信頼性の担保に使う。

## 確認方法の区分
- **A: 一次情報の本文を確認**（公的機関・当事者の公式文書を読んだ）
- **B: 複数の信頼できる報道・専門家解説で照合**（本文未読だが、独立した2つ以上のソースが一致）
- **C: 単一ソース**（要追加確認）

## 2026-09-24（Step 1）

作業環境のネットワーク制限でページ本文を取得できなかったため、今回の確認はすべて **B（検索結果の複数ソース照合）** で行った。
次回、一次情報の本文を確認できる環境で **A** に格上げする。

| 記事 | 項目 | 区分 | 次回の対応 |
|---|---|---|---|
| domains/games.md | Steam AI開示ルール（2026年1月改定） | B | Steamworksの公式ドキュメントで文言を確認 |
| domains/music.md | Suno/Udio訴訟・和解の状況 | B | 各社プレスリリース・訴状で確認。2026年7月の審理結果を追跡 |
| domains/film-video.md | SAG-AFTRA 2026年契約のAI条項 | B | SAG-AFTRA公式の条項要約で確認 |
| domains/film-video.md | WGA 2026年MBAのAI条項 | **C（未確認）** | MOA本文（wga.org）で確認 |
| domains/characters-vtuber-live.md / ethics-legal | NY州・カリフォルニア州SB 243・中国暫定弁法・FTC 6(b) | B | 条文・FTC公式発表で確認 |
| ethics-legal | Character.AI訴訟の和解（2026年1月） | B | 裁判所記録・主要報道で確認 |
| ethics-legal | フェアユース判断（ROSS / Bartz / Kadrey） | B | 判決文で確認。第3巡回区のROSS控訴審判決を追跡 |
| ethics-legal | EU AI Act（GPAI義務・第50条・Omnibus猶予） | B | 官報掲載のOmnibus最終版で猶予期間を確認 |
| ethics-legal | 法務省「生成AIによるパブリシティ権侵害等に関する解釈指針」（2026年8月7日） | B | 報告書PDF本文で要件・例示を確認 |
| ethics-legal | ELVIS法・NO FAKES Act | B | 法案の進捗を追跡 |

## 2026-09-24（本文確認: Step 1の続き）

ネットワーク許可を追加し、一次情報・主要報道の**本文**を読んで再確認した。

| 記事 | 項目 | 区分 | 確認した資料 | 結果 |
|---|---|---|---|---|
| ethics-legal / games | 法務省「生成AIによるパブリシティ権侵害等に関する解釈指針」 | **A** | 報告書PDF本文 | 正しかった。判断基準（3類型、似た声でも識別できれば該当）、侵害例の一覧、**声優は名前・顔が知られていなくてよい**、**実在の人の声でないキャラの声は対象外**を追記 |
| film-video | WGA 2026年MBAのAI条項 | **A** | WGA公式の契約概要 | 前回は未確認だった。2023年のAI保護を維持し、商用の生成AI学習用ライセンスに書面通知義務が加わったことを確認。`【要確認】` を解消 |
| ethics-legal / characters / games | カリフォルニア州SB 243 | **A** | 州議会の条文 | 大筋は正しかった。**ゲーム内ボットの適用除外**、2027年7月からの年次報告、損害賠償額（実損害か1違反1,000ドルの大きい方）を追記。休憩リマインドは「未成年と分かっている利用者」が対象 |
| ethics-legal | FTC 6(b)調査 | **A** | FTCのプレスリリース | 正しかった。7社の中にInstagramが抜けていたので修正 |
| ethics-legal | EU AI Act 第50条 | **A** | 欧州委員会FAQ、条文 | **修正**: 2026年12月2日までの猶予は**50条2項（マーキング）だけ**。「芸術作品の例外」は50条4項（ディープフェイク）の規定と特定 |
| film-video | SAG-AFTRA 2026年契約 | B | Variety、The Hollywood Reporterの本文 | **修正**: 「写真からのレプリカも保護」「吹替に同意が必要」は本文で確認できなかったので削除。確認できた内容（大きな付加価値の要件、最低報酬、スキャン理由、学習ライセンスの通知・協議）に置き換え |
| music | Suno/Udio訴訟 | B | Variety、Music Business Worldwideの本文と見出し | 正しかった。和解日（UMG×Udio 2025年10月29日、Warner 2025年11月）、60,202曲、Suno側の主張、UMGの方針を追記 |
| ethics-legal / characters | 中国「擬人化AIインタラクションサービス管理暫定弁法」 | B | Bird & Bird の解説本文 | 正しかった。連続2時間超の通知、依存兆候への対応、アプリストアの確認義務を追記。CAC公式の原文は未確認 |
| ethics-legal | NO FAKES Act | B | Holland & Knight の解説本文 | 正しかった。口頭採決であること、下院の状況を追記。congress.govはボット対策で取得できず |
| ethics-legal | Character.AI和解 | B | CNN、CNBC（検索結果） | 正しかった。2026年1月7日の裁判所提出書面、4州5件、条件非公開・責任は認めず、を追記 |
| games | Steam AI開示ルール | B | Game Developer の本文 | 正しかった。Steamworksの公式文書はログインが必要で未確認 |
| ethics-legal | ROSS控訴審 | B | 複数の法律事務所の解説 | 2026年9月時点で判決はまだ |
| ethics-legal | 米ニューヨーク州のAIコンパニオン法 | B | 条文（一般事業法1702条、Justia掲載）の文言を検索結果で確認。本文ページはネットワーク許可外で未取得 | **解消**: 通知は**未成年に限らず全利用者**が対象（開始時は1日1回まで、継続中は3時間ごと）。未成年に限定していたのはカリフォルニア州法で、解説記事が両者を混同していた。対応手順の対象に「他人への身体的・経済的な危害」も含まれることを追記 |

### 取得できなかったサイト（ボット対策やネットワーク許可外）
sagaftra.org、nysenate.gov、congress.gov、governor.ny.gov、indiewire.com、cac.gov.cn（正しいURLが未特定）。次回はブラウザ機能を使うか、別の公式ミラーを探す。

## 2026-09-25（事例分析・国別法務の追加）

| 記事 | 項目 | 区分 | 確認した資料 |
|---|---|---|---|
| domains/case-studies.md | 映像・音楽・アニメ/マンガの事例14件 | B | 各事例に付けた報道・公式発表（検索結果の本文要約で照合）。F04 のディズニー発表、A05 のCODA要望書、M04 のDeezer発表は当事者の公式ページ |
| ethics-legal/by-country/china.md | 表示弁法（2025年9月1日施行） | B | Loeb & Loeb、China Law Translate の解説 |
| ethics-legal/by-country/china.md | 生成AIサービス暫定弁法の学習データ要件 | B | China Law Translate の英訳・China Briefing の解説で第7条を確認。**解消** |
| ethics-legal/by-country/china.md | 民法典1023条（声）と北京インターネット法院の判決（2024年4月） | B | King & Wood Mallesons、Linklaters の解説。**解消** |
| ethics-legal/by-country/korea.md | 学習と著作権（TDM例外は未成立） | B | Asia IP、IT Brief Asia の報道。**解消** |
| domains/case-studies.md | 追加16件（F06〜F10、M05〜M10、A06〜A10） | B | 各事例に付けた報道・公式ページ（検索結果の要約で照合） |
| ethics-legal/by-country/korea.md | AI基本法（2026年1月22日施行、表示義務、過料猶予） | B | 米国商務省、Cooley、FPF の解説 |

## 追跡中の案件（結果が出たら更新）
- Thomson Reuters v. ROSS 第3巡回区判決（AI学習のフェアユースに関する初の連邦控訴審判断）
- UMG・Sony v. Suno（v6モデルを対象とした2026年9月の新訴訟を含む）
- NO FAKES Act の本会議審議
- EU AI Act 第50条の実務指針・行動規範（Code of Practice）の最終版
- 日本の不正競争防止法改正（声の保護）の検討状況
