import XCTest
@testable import OrbitSwitch

final class L10nTests: XCTestCase {
    override func tearDown() {
        L10n.lang = "en"
        super.tearDown()
    }

    func testBothLanguagesHaveTheSameKeys() {
        XCTAssertEqual(Set(L10nTable.ja.keys), Set(L10nTable.en.keys))
    }

    func testEnglishHasNoJapanese() {
        for (key, value) in L10nTable.en where key != "menu.lang" {
            XCTAssertNil(value.range(of: "[\\u3040-\\u30ff\\u4e00-\\u9fff]", options: .regularExpression), "\(key): \(value)")
        }
    }

    func testResolveFollowsDeviceLanguageUnlessChosen() {
        XCTAssertEqual(L10n.resolve("auto", preferred: ["ja-JP", "en"]), "ja")
        XCTAssertEqual(L10n.resolve("auto", preferred: ["en-US"]), "en")
        XCTAssertEqual(L10n.resolve("auto", preferred: ["pt-BR"]), "en")
        XCTAssertEqual(L10n.resolve("en", preferred: ["ja-JP"]), "en")
        XCTAssertEqual(L10n.resolve("ja", preferred: ["en-US"]), "ja")
    }

    func testMissionAndSkinNamesAreTranslated() {
        L10n.lang = "en"
        XCTAssertEqual(MissionKind.gems.text(5), "Collect 5 gems in one run")
        XCTAssertEqual(Skins.find("sakura").name, "Sakura")
        L10n.lang = "ja"
        XCTAssertEqual(MissionKind.gems.text(5), "ワンプレイでジェム5個")
        XCTAssertEqual(Skins.find("sakura").name, "サクラ")
    }

    func testPlaceholdersAndFallback() {
        L10n.lang = "en"
        XCTAssertEqual(L10n.t("over.tease.close", ["n": 3]), "So close! 3 more to beat your best!")
        XCTAssertEqual(L10n.t("no.such.key"), "no.such.key")
    }

    func testLanguageSettingIsSanitized() throws {
        let s = try JSONDecoder().decode(SaveData.self, from: Data(#"{"lang":"klingon"}"#.utf8))
        XCTAssertEqual(s.lang, "auto")
        let e = try JSONDecoder().decode(SaveData.self, from: Data(#"{"lang":"en"}"#.utf8))
        XCTAssertEqual(e.lang, "en")
    }
}
