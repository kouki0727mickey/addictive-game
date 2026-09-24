/*
 * ORBIT SWITCH — UI strings in Japanese and English.
 * `{name}` placeholders are filled by t(key, { name: value }).
 * Works in the browser (window.OrbitI18n) and in Node (require) for tests.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.OrbitI18n = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const STRINGS = {
    ja: {
      'meta.description': 'タップだけで遊べる中毒性ワンタップゲーム。内側と外側のリングを切り替えてトゲをよけ、ジェムを集めてフィーバーを狙え。',
      'canvas.label': 'ゲーム画面：タップまたはスペースキーでリングを切り替え',
      'menu.tagline': 'タップで内側⇄外側。<wbr>トゲをよけて<wbr>ジェムを集めろ。',
      'menu.play': 'タップでスタート',
      'menu.daily': '📅 今日のチャレンジ',
      'menu.new': 'NEW',
      'menu.skins': 'スキン',
      'menu.missions': 'ミッション',
      'menu.sound': 'サウンド切替',
      'menu.lang': '言語を切り替え（English）',
      'menu.haptics': '振動切替',
      'menu.taglineApp': 'タップで内側⇄外側。\nトゲをよけてジェムを集めろ。',
      'menu.dailyBonus': 'デイリーボーナス 🪙+{bonus}（{streak}日連続）',
      'pause.title': '一時停止',
      'pause.resume': 'タップで再開',
      'pause.hint': 'Esc / P でも一時停止・再開できます',
      'over.daily': '📅 今日のチャレンジ',
      'over.try': '（{n}回目）',
      'over.tease.newBest': '記録更新！ +{n}',
      'over.tease.zero': 'トゲをよけると1点！ タップで内⇄外を切替',
      'over.tease.first': '初記録！ 次はこれを超えよう',
      'over.tease.tied': 'ベストに並んだ！ あと1点で更新！',
      'over.tease.close': 'おしい！ あと{n}点でベスト更新！',
      'over.tease.far': 'ベストまで あと{n}点',
      'over.gems': 'ジェム',
      'over.bestCombo': '最大コンボ',
      'over.nearMisses': 'ニアミス',
      'over.smashed': '粉砕',
      'over.levelUp': 'レベルアップ!',
      'over.canUnlock': '🔓 スキン「{name}」を解放できます！',
      'over.nextUnlock': '次のスキン「{name}」まで 🪙{n}',
      'over.menu': 'メニュー',
      'over.share': 'スコアを共有',
      'over.retry': 'もう一回 ↻',
      'share.normal': 'ORBIT SWITCH で {score}点！（ベスト {best}）タップだけの中毒ゲーム #ORBITSWITCH',
      'share.daily': 'ORBIT SWITCH 今日のチャレンジ（{day}）で {score}点！ 同じステージで勝負しよう #ORBITSWITCH',
      'share.copied': 'コピーしました！',
      'share.failed': 'コピーできませんでした',
      'shop.title': 'スキン',
      'shop.equipped': '使用中',
      'shop.owned': '所持',
      'shop.buy': '購入',
      'shop.notEnough': 'コインが足りません（あと 🪙{n}）— プレイして集めよう！',
      'back': 'もどる',
      'missions.title': 'ミッション',
      'missions.lifetime': '通算 {plays} プレイ ・ ジェム {gems} 個 ・ Lv {level}',
      'mission.score': 'ワンプレイで{n}点',
      'mission.gems': 'ワンプレイでジェム{n}個',
      'mission.nearMisses': 'ワンプレイでニアミス{n}回',
      'mission.bestCombo': 'コンボ{n}達成',
      'mission.feverCount': 'ワンプレイでフィーバー{n}回',
      'mission.plays': '{n}回プレイ',
      'skin.neon': 'ネオン',
      'skin.sakura': 'サクラ',
      'skin.lime': 'ライム',
      'skin.sun': 'サン',
      'skin.void': 'ヴォイド',
      'skin.ghost': 'ゴースト',
      'skin.rainbow': 'レインボー',
      'hud.combo': '{n} combo',
      'hint.start': 'タップで\n内⇄外',
    },
    en: {
      'meta.description': 'A one-tap game you can’t put down. Switch between the inner and outer ring, dodge spikes, grab gems and chase the fever.',
      'canvas.label': 'Game screen: tap or press Space to switch rings',
      'menu.tagline': 'Tap to switch rings.<wbr> Dodge spikes,<wbr> grab gems.',
      'menu.play': 'TAP TO PLAY',
      'menu.daily': '📅 Daily Challenge',
      'menu.new': 'NEW',
      'menu.skins': 'Skins',
      'menu.missions': 'Missions',
      'menu.sound': 'Toggle sound',
      'menu.lang': 'Switch language (日本語)',
      'menu.haptics': 'Toggle vibration',
      'menu.taglineApp': 'Tap to switch rings.\nDodge spikes, grab gems.',
      'menu.dailyBonus': 'Daily bonus 🪙+{bonus} · {streak}-day streak',
      'pause.title': 'Paused',
      'pause.resume': 'Tap to resume',
      'pause.hint': 'Esc / P also pauses and resumes',
      'over.daily': '📅 Daily Challenge',
      'over.try': ' (try {n})',
      'over.tease.newBest': 'New record! +{n}',
      'over.tease.zero': 'Dodge a spike for 1 point! Tap to switch rings',
      'over.tease.first': 'First score! Now beat it',
      'over.tease.tied': 'Tied your best! 1 more point to beat it!',
      'over.tease.close': 'So close! {n} more to beat your best!',
      'over.tease.far': '{n} points to your best',
      'over.gems': 'Gems',
      'over.bestCombo': 'Best combo',
      'over.nearMisses': 'Near misses',
      'over.smashed': 'Smashed',
      'over.levelUp': 'Level up!',
      'over.canUnlock': '🔓 You can unlock the {name} skin!',
      'over.nextUnlock': '🪙{n} to the {name} skin',
      'over.menu': 'Menu',
      'over.share': 'Share score',
      'over.retry': 'Retry ↻',
      'share.normal': 'I scored {score} in ORBIT SWITCH! (best {best}) One tap, can’t stop. #ORBITSWITCH',
      'share.daily': 'I scored {score} in today’s ORBIT SWITCH Daily Challenge ({day})! Same stage for everyone — beat me. #ORBITSWITCH',
      'share.copied': 'Copied!',
      'share.failed': 'Couldn’t copy',
      'shop.title': 'Skins',
      'shop.equipped': 'Equipped',
      'shop.owned': 'Owned',
      'shop.buy': 'Buy',
      'shop.notEnough': 'Not enough coins (🪙{n} more) — play to earn more!',
      'back': 'Back',
      'missions.title': 'Missions',
      'missions.lifetime': '{plays} plays · {gems} gems · Lv {level}',
      'mission.score': 'Score {n} in one run',
      'mission.gems': 'Collect {n} gems in one run',
      'mission.nearMisses': '{n} near misses in one run',
      'mission.bestCombo': 'Reach a {n} combo',
      'mission.feverCount': 'Trigger fever {n}× in one run',
      'mission.plays': 'Play {n} times',
      'skin.neon': 'Neon',
      'skin.sakura': 'Sakura',
      'skin.lime': 'Lime',
      'skin.sun': 'Sun',
      'skin.void': 'Void',
      'skin.ghost': 'Ghost',
      'skin.rainbow': 'Rainbow',
      'hud.combo': '{n} combo',
      'hint.start': 'TAP TO\nSWITCH',
    },
  };

  const LANGS = ['ja', 'en'];

  // Japanese only when the user's first preferred language is Japanese; English for everyone else.
  function detect(languages) {
    const first = (languages && languages[0]) || 'en';
    return /^ja\b/i.test(first) ? 'ja' : 'en';
  }

  // setting: 'auto' | 'ja' | 'en'
  function resolve(setting, languages) {
    return LANGS.indexOf(setting) !== -1 ? setting : detect(languages);
  }

  function create(lang) {
    const table = STRINGS[lang] || STRINGS.en;
    return function t(key, vars) {
      let s = table[key];
      if (s === undefined) s = STRINGS.en[key];
      if (s === undefined) return key;
      if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
      return s;
    };
  }

  return { STRINGS, LANGS, detect, resolve, create };
});
