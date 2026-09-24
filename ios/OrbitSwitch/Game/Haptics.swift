// Haptics through the iPhone's Taptic Engine (UIFeedbackGenerator).
// iPads have no vibration motor: the calls are simply no-ops there.

import UIKit

final class Haptics {
    var enabled = true

    private let light = UIImpactFeedbackGenerator(style: .light)
    private let soft = UIImpactFeedbackGenerator(style: .soft)
    private let rigid = UIImpactFeedbackGenerator(style: .rigid)
    private let heavy = UIImpactFeedbackGenerator(style: .heavy)
    private let notify = UINotificationFeedbackGenerator()

    /// Wakes the Taptic Engine so the first tap of a run has no latency.
    func prepare() {
        guard enabled else { return }
        light.prepare()
        rigid.prepare()
        heavy.prepare()
    }

    /// Every ring switch: a crisp, light tick.
    func switchRing() {
        guard enabled else { return }
        light.impactOccurred(intensity: 0.6)
        light.prepare()
    }

    func gem() {
        guard enabled else { return }
        soft.impactOccurred(intensity: 0.5)
    }

    /// Dodged a spike at the last moment.
    func nearMiss() {
        guard enabled else { return }
        rigid.impactOccurred(intensity: 1.0)
    }

    func smash() {
        guard enabled else { return }
        heavy.impactOccurred(intensity: 0.7)
    }

    func fever() {
        guard enabled else { return }
        notify.notificationOccurred(.success)
    }

    func death() {
        guard enabled else { return }
        heavy.impactOccurred(intensity: 1.0)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.09) { [weak self] in
            guard let self, self.enabled else { return }
            self.notify.notificationOccurred(.error)
        }
    }

    func celebrate() {
        guard enabled else { return }
        notify.notificationOccurred(.success)
    }

    func denied() {
        guard enabled else { return }
        notify.notificationOccurred(.warning)
    }
}
