---
title: AI × エンタメの倫理と法務
domain: ethics-legal
maturity: L1
last_reviewed: 2026-09-24
tags: [copyright, publicity, voice, regulation, ethics]
---

# AI × エンタメの倫理と法務

> ⚠️ 本記事は一般的な情報整理であり、法的助言ではない。法制度・判例・ガイドラインは変化が速いため、
> 実務判断は必ず最新の一次情報と専門家の確認に基づくこと。

## 一言で言うと
論点は大きく **「学習（入力）」「生成物（出力）」「人格（声・顔・名前）」「利用者保護」** の4つ。
国によって考え方が大きく異なり、特に日本は学習段階で比較的柔軟な制度を持つ一方、生成・利用段階では通常の著作権侵害判断が適用される。

## 1. 学習（入力）段階

### 日本
- 著作権法 **第30条の4**: 情報解析など「著作物に表現された思想又は感情の享受を目的としない利用」について、一定の条件下で許諾なく利用できる
- ただし「著作権者の利益を不当に害する場合」は除外される
- 文化庁「AIと著作権に関する考え方について」（2024年）で、特定のクリエイターの作品を意図的に模倣・出力させる目的の追加学習などは「享受目的」が併存するとして適用外になり得る、といった整理が示されている

### 米国
- 学習がフェアユースに当たるかが多数の訴訟で争われている。2026年9月時点の主な判断[^fairuse]:
  | 事件 | 判断 | ポイント |
  |---|---|---|
  | Thomson Reuters v. ROSS（2025年2月、地裁） | フェアユース**否定** | 生成AIではなく、競合する法律検索サービスの学習。控訴審（第3巡回区）で2026年6月に口頭弁論。**AI学習のフェアユースに関する初の連邦控訴審判断**になる見込み |
  | Bartz v. Anthropic（2025年6月、地裁） | 合法に入手した書籍での学習はフェアユース**肯定** | 海賊版で恒久的なライブラリを作った点はフェアユースに当たらない → 15億ドルで和解 |
  | Kadrey v. Meta（2025年6月、地裁） | フェアユース**肯定**（原告の立証不足） | 変容性だけでは足りず、**市場への影響**が重要と強調 |
- 💡示唆: 「学習そのもの」より **「データの入手方法」と「市場の代替」** が争点の中心になっている

### EU
- テキスト・データマイニング例外（権利者はオプトアウト可能）
- **EU AI Act**[^euai]
  - 汎用AI（GPAI）モデル提供者の義務: **2025年8月2日から適用**。欧州委員会の所定テンプレートで学習データの概要を公開する（それ以前に市場投入済みのモデルは2027年8月2日まで猶予）。AI Officeによる執行は2026年8月2日から
  - 第50条の透明性義務: **2026年8月2日から適用**（欧州委員会FAQ）
    - 50条1項: 人と直接やり取りするAIは、AIであることを利用者に知らせる（状況から明らかな場合を除く）→ **会話NPC・AIキャラに直結**
    - 50条2項: 合成音声・画像・動画・テキストを生成するAIの提供者は、出力を機械可読な形式でマーキングする。**猶予はこの2項だけ**で、2026年8月2日より前に市場投入済みのシステムは2026年12月2日から適用（Digital Omnibusによる改正）
    - 50条4項: ディープフェイクを公開する者はAI生成であることを開示する。ただし**明らかに芸術的・創作的・風刺的・フィクションの作品**の一部であれば、作品の鑑賞を妨げない適切な方法で「生成コンテンツが含まれること」を示せばよい
    - 2026年8月2日より前に生成されたコンテンツを遡って表示する義務はない

## 2. 生成物（出力）段階
- 生成物が既存作品と **類似** し、かつ既存作品に **依拠** していれば、日本でも侵害になり得る（通常の判断枠組み）
- AI生成物の **著作権の成立**: 人間の創作的寄与がなければ著作物と認められにくい（日米とも同様の方向性）。
  → 「AIで作ったものを自社IPとして守れるか」はビジネス上の重要論点

## 3. 人格（声・顔・名前）
- **日本**: パブリシティ権（判例で認められた、顧客吸引力の保護）、肖像権、不正競争防止法などで対応。声を直接保護する条文はないが、解釈指針が出た[^jpvoice]
  - 法務省の検討会が2026年8月7日に報告書「生成AIによるパブリシティ権侵害等に関する解釈指針」を公表
  - **声も**、肖像と同様に、パブリシティ権および「みだりに利用されない権利」の保護対象に含まれるとの解釈を明示
  - 判断基準: 肖像と同じく、ピンク・レディー事件最高裁判決の3類型（①声そのものを鑑賞対象の商品にする、②商品の差別化のために声を付す、③広告に使う）など、「専ら声の顧客吸引力の利用を目的とする」場合に侵害となる
  - 「本人の声」かどうか: 同一の声だけでなく、**似た声でも**、類似の程度と「本人を想起させる情報」（名前・キャラ名の表示など）を総合して、客が本人の声と識別できれば「本人の声の使用」に当たる
  - 侵害例として報告書が挙げるもの: ボイスメッセージ、ボイススタンプ、オーディオブック、**AIカバー**、ナレーション、目覚まし時計、カーナビ、スマートスピーカー、広告ナレーション
  - **声優**: 声そのものに販売を促す力があれば足り、声優の名前や顔が広く知られている必要はない
  - **実在の人の声ではないキャラクターの声**（合成音声で一から作った声など）は、パブリシティ権で守られる顧客吸引力の対象外
  - 人間による「ものまね・声まね」は、本人と誤解されるような場合でない限り侵害にならない
  - 💡ゲーム・キャラ事業への示唆: AIボイスは「実在の声優の声を許諾を得て使う」か「実在の人に似せない声を一から作る」かのどちらかに寄せる。有名声優に**似せた**声は、名前を出さなくても侵害になり得る
  - 知的財産推進計画2026では、不正競争防止法の改正を含む法的措置の検討継続も示されている
- **米国**: 州法レベルで声・肖像のAI模倣を規制（例: テネシー州のELVIS法。2024年7月施行、声の「シミュレーション」も明示的に保護）。連邦レベルでは「NO FAKES Act」（S. 4591）が2026年6月18日に上院司法委員会を全会一致（口頭採決）で通過し、上院本会議へ。下院にも対応法案が出ているが、下院司法委員会は未審議。成立は未定[^usvoice]
- 実務: 声優・俳優との契約に **AI利用の範囲・期間・報酬・撤回条件** を明記する

## 4. 利用者保護
- **ガチャ・確率型アイテム**: 日本の景品表示法（コンプガチャ規制）、各国のルートボックス規制、業界団体の自主規制
- **未成年保護**: 年齢に応じたコンテンツ・課金制限
- **AIコンパニオン**: 依存・未成年・危機対応について、規制が既に施行されている[^companion]
  | 地域 | 規制 | 施行 | 主な義務 |
  |---|---|---|---|
  | 米ニューヨーク州 | AIコンパニオン安全規定 | 2025年11月5日 | AIであることの通知（3時間ごとの定期通知を含む。対象が全利用者か未成年のみかは解説により記述が分かれる【要確認: 条文】）、自傷・自殺兆候の検知と相談窓口への誘導。州司法長官が執行（1日最大1.5万ドルの民事罰） |
  | 米カリフォルニア州 | SB 243 | 2026年1月1日 | 人間と誤認され得る場合のAI通知、自傷・自殺コンテンツ防止のプロトコルとその公開、未成年と分かっている利用者には AI開示・3時間ごとの休憩リマインド・性的コンテンツの防止、2027年7月から年次報告。**損害を受けた本人が訴訟可能**（実損害か1違反1,000ドルの大きい方）。**ゲーム内のボットで、ゲームに関係する返答に限られ、メンタルヘルス・自傷・性的な話題やゲーム外の会話ができないものは対象外** |
  | 中国 | 擬人化AIインタラクションサービス管理暫定弁法 | 2026年7月15日 | 未成年への「仮想の恋人・家族」型サービスの禁止、14歳未満は保護者の同意、未成年の識別と未成年モード（利用時間制限、課金制限など）の義務化、AIであることの明示、**連続2時間を超える利用で利用時間のポップアップ通知**、過度な依存の兆候を検知したら注意喚起、アプリストアは安全評価を確認して未対応アプリを掲載しない |
  | 米連邦取引委員会（FTC） | 6(b)調査 | 2025年9月開始 | Alphabet、Character Technologies（Character.AI）、Instagram、Meta、OpenAI、Snap、xAIの7社に、子ども・十代への安全対策の報告を命令 |
  - 訴訟: Character.AI、その創業者、Googleは、子どもの自殺・深刻な精神的被害をめぐる訴訟5件（フロリダ、コロラド、ニューヨーク、テキサス）で和解に合意（2026年1月7日の裁判所提出書面）。条件は非公開で、責任は認めていない
  - 💡ゲームへの示唆: カリフォルニア州法の除外規定から逆算すると、**「ゲームの話題に限定したNPC」は規制対象外になり得るが、雑談・恋愛・悩み相談ができるキャラはコンパニオン扱い**になる。キャラの会話範囲は、体験設計と同時に法的な分類を決める設計判断になる
- **透明性**: AIとの対話であることの明示、AI生成コンテンツの表示（EU AI Actの透明性義務等）
- **個人データ**: 会話ログ・記憶データの取り扱い（個人情報保護法、GDPR等）

## 実践チェックリスト
- [ ] 学習データの出所と権利処理を記録しているか
- [ ] 特定作家・作品の模倣を目的とした学習・生成をしていないか
- [ ] 生成物の類似性チェックの工程があるか
- [ ] 声・肖像の利用について本人と契約しているか
- [ ] 生成物の著作権が必要な場合、人間の創作的寄与を記録しているか
- [ ] AI使用の開示方針を決めているか
- [ ] 未成年・脆弱なユーザーの保護策があるか
- [ ] 展開する国ごとの規制を確認したか

## 参考（一次情報）
- 文化庁「AIと著作権について」関連資料
- 米国著作権局 Copyright and Artificial Intelligence 報告書
- EU AI Act 本文

## 参考文献（確認日: 2026-09-24）
[^fairuse]: Skadden「Fair Use and AI Training」https://www.skadden.com/insights/publications/2025/07/fair-use-and-ai-training ／ Kluwer Copyright Blog（Bartz和解）https://legalblogs.wolterskluwer.com/copyright-blog/the-bartz-v-anthropic-settlement-understanding-americas-largest-copyright-settlement/ ／ Baker Botts（ROSS控訴審）https://www.bakerbotts.com/thought-leadership/publications/2026/july/third-circuit-hears-oral-argument
[^euai]: 欧州委員会「Transparency obligations under Article 50 of the AI Act」FAQ（施行日・猶予の確認）https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act ／ AI Act Service Desk（第50条本文）https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50 ／ Mayer Brown（GPAI義務の適用開始）https://www.mayerbrown.com/en/insights/publications/2025/08/eu-ai-act-news-rules-on-general-purpose-ai-start-applying-guidelines-and-template-for-summary-of-training-data-finalized
[^jpvoice]: 法務省「肖像、声等の無断利用による民事責任の在り方に関する検討会 取りまとめ報告書―生成AIによるパブリシティ権侵害等に関する解釈指針―」（令和8年8月。第1章第1の3「声のパブリシティ権侵害の判断基準」を本文で確認） ／ 検討会ページhttps://www.moj.go.jp/MINJI/minji07_00400.html ／ 報告書PDF https://www.moj.go.jp/content/001468286.pdf ／ ITmedia AI+ https://www.itmedia.co.jp/aiplus/article/2608/07/2000000452/ ／ 時事ドットコム https://www.jiji.com/jc/article?k=2026080700713&g=soc
[^usvoice]: Holland & Knight（NO FAKES Act委員会通過）https://www.hklaw.com/en/insights/publications/2026/06/senate-judiciary-committee-advances-legislation-to-protect-name ／ Holland & Knight（ELVIS法）https://www.hklaw.com/en/insights/publications/2024/04/first-of-its-kind-ai-law-addresses-deep-fakes-and-voice-clones
[^companion]: カリフォルニア州議会 SB 243 条文 https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB243 ／ Fenwick（NY州）https://www.fenwick.com/insights/publications/new-yorks-ai-companion-safeguard-law-takes-effect ／ Future of Privacy Forum（SB 243）https://fpf.org/blog/understanding-the-new-wave-of-chatbot-legislation-california-sb-243-and-beyond/ ／ Bird & Bird（中国）https://www.twobirds.com/en/insights/2026/china/china's-new-regulations-on-ai-anthropomorphic-interactive-services ／ FTC https://www.ftc.gov/news-events/news/press-releases/2025/09/ftc-launches-inquiry-ai-chatbots-acting-companions ／ CNN（Character.AI和解）https://edition.cnn.com/2026/01/07/business/character-ai-google-settle-teen-suicide-lawsuit ／ CNBC https://www.cnbc.com/2026/01/07/google-characterai-to-settle-suits-involving-suicides-ai-chatbots.html
