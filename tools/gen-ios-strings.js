// Generates ios/OrbitSwitch/Core/Strings.generated.swift from js/i18n.js,
// so the web and iOS versions share one set of translations.
// Usage: node tools/gen-ios-strings.js [--check]
const fs = require('fs');
const path = require('path');
const I18n = require('../js/i18n.js');

const OUT = path.join(__dirname, '..', 'ios', 'OrbitSwitch', 'Core', 'Strings.generated.swift');

function swiftString(s) {
  const json = JSON.stringify(s); // escapes " \ and newlines the same way Swift does
  if (/\\u[0-9a-fA-F]{4}/.test(json)) throw new Error('unsupported escape in: ' + s);
  return json;
}

function generate() {
  const lines = ['// GENERATED from js/i18n.js by tools/gen-ios-strings.js. Do not edit by hand.', '', 'enum L10nTable {'];
  for (const lang of I18n.LANGS) {
    lines.push('    static let ' + lang + ': [String: String] = [');
    for (const key of Object.keys(I18n.STRINGS[lang]).sort()) {
      lines.push('        ' + swiftString(key) + ': ' + swiftString(I18n.STRINGS[lang][key]) + ',');
    }
    lines.push('    ]');
  }
  lines.push('}', '');
  return lines.join('\n');
}

module.exports = { generate, OUT };

if (require.main === module) {
  const code = generate();
  if (process.argv.includes('--check')) {
    const current = fs.existsSync(OUT) ? fs.readFileSync(OUT, 'utf8') : '';
    if (current !== code) {
      console.error('Strings.generated.swift is out of date: run `npm run gen:ios`');
      process.exit(1);
    }
    console.log('Strings.generated.swift is up to date');
  } else {
    fs.writeFileSync(OUT, code);
    console.log('wrote ' + path.relative(process.cwd(), OUT));
  }
}
