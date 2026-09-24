// Japanese / English UI strings. The tables are generated from js/i18n.js (shared with the web version).

import Foundation

enum L10n {
    /// "ja" or "en"; set from the save's language setting at launch and when the player switches.
    static var lang = "en"

    /// setting: "auto" | "ja" | "en". "auto" follows the device (and iOS's per-app language setting):
    /// Japanese for Japanese, English for everyone else.
    static func resolve(_ setting: String, preferred: [String] = Bundle.main.preferredLocalizations + Locale.preferredLanguages) -> String {
        if setting == "ja" || setting == "en" { return setting }
        return (preferred.first ?? "en").hasPrefix("ja") ? "ja" : "en"
    }

    static func t(_ key: String, _ vars: [String: CustomStringConvertible] = [:]) -> String {
        let table = lang == "ja" ? L10nTable.ja : L10nTable.en
        var s = table[key] ?? L10nTable.en[key] ?? key
        for (k, v) in vars { s = s.replacingOccurrences(of: "{\(k)}", with: v.description) }
        return s
    }
}
