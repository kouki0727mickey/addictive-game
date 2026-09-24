const test = require('node:test');
const assert = require('node:assert');
const I18n = require('../js/i18n.js');
const Meta = require('../js/meta.js');

const placeholders = (s) => (s.match(/\{\w+\}/g) || []).sort().join(',');

test('every key exists in every language with the same placeholders', () => {
  const [a, b] = I18n.LANGS.map((l) => I18n.STRINGS[l]);
  assert.deepStrictEqual(Object.keys(a).sort(), Object.keys(b).sort());
  for (const k of Object.keys(a)) assert.strictEqual(placeholders(a[k]), placeholders(b[k]), 'placeholders differ for ' + k);
});

test('every skin and mission kind has a name in every language', () => {
  for (const lang of I18n.LANGS) {
    for (const s of Meta.SKINS) assert.ok(I18n.STRINGS[lang]['skin.' + s.id], lang + ' skin.' + s.id);
    for (const m of Meta.MISSION_POOL) assert.ok(I18n.STRINGS[lang]['mission.' + m.kind], lang + ' mission.' + m.kind);
  }
});

test('English strings contain no Japanese characters', () => {
  for (const [k, v] of Object.entries(I18n.STRINGS.en)) {
    if (k === 'menu.lang') continue; // intentionally names the other language: "(日本語)"
    assert.ok(!/[\u3040-\u30ff\u4e00-\u9fff]/.test(v), k + ': ' + v);
  }
});

test('language detection: Japanese only for ja, English otherwise', () => {
  assert.strictEqual(I18n.detect(['ja-JP', 'en-US']), 'ja');
  assert.strictEqual(I18n.detect(['ja']), 'ja');
  assert.strictEqual(I18n.detect(['en-US', 'ja-JP']), 'en');
  assert.strictEqual(I18n.detect(['pt-BR']), 'en');
  assert.strictEqual(I18n.detect([]), 'en');
  assert.strictEqual(I18n.resolve('auto', ['ja-JP']), 'ja');
  assert.strictEqual(I18n.resolve('en', ['ja-JP']), 'en');
  assert.strictEqual(I18n.resolve('ja', ['en-US']), 'ja');
});

test('t() fills placeholders and falls back sensibly', () => {
  const t = I18n.create('en');
  assert.strictEqual(t('over.tease.close', { n: 3 }), 'So close! 3 more to beat your best!');
  assert.strictEqual(t('missing.key'), 'missing.key');
  assert.strictEqual(I18n.create('xx')('back'), 'Back');
  assert.strictEqual(I18n.create('ja')('mission.gems', { n: 5 }), 'ワンプレイでジェム5個');
});

test('iOS strings are generated from the current js/i18n.js', () => {
  const fs = require('fs');
  const { generate, OUT } = require('../tools/gen-ios-strings.js');
  assert.strictEqual(fs.readFileSync(OUT, 'utf8'), generate(), 'run `npm run gen:ios`');
});
