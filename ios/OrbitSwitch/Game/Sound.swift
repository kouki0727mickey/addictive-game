// Tiny synthesizer: every sound effect is rendered once into a PCM buffer at start-up
// (no audio assets), then played on a small pool of player nodes.

import AVFoundation

final class Sound {
    enum Wave { case sine, triangle, square, saw }

    struct Note {
        var freq: Double
        var dur: Double
        var wave: Wave
        var vol: Double
        var slide: Double? = nil
        var delay: Double = 0
    }

    var enabled = true

    private let engine = AVAudioEngine()
    private let format = AVAudioFormat(standardFormatWithSampleRate: 44_100, channels: 1)!
    private var players: [AVAudioPlayerNode] = []
    private var nextPlayer = 0
    private var buffers: [String: AVAudioPCMBuffer] = [:]
    private var started = false

    static let scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]

    init() {
        // .ambient: respects the silent switch and mixes with the player's own music.
        try? AVAudioSession.sharedInstance().setCategory(.ambient, options: [.mixWithOthers])
        for _ in 0..<8 {
            let p = AVAudioPlayerNode()
            engine.attach(p)
            engine.connect(p, to: engine.mainMixerNode, format: format)
            players.append(p)
        }
        engine.mainMixerNode.outputVolume = 0.5
        buildSounds()
    }

    private func semis(_ base: Double, _ n: Int) -> Double { base * pow(2, Double(n) / 12) }

    private func buildSounds() {
        buffers["switch"] = render([Note(freq: 520, dur: 0.05, wave: .triangle, vol: 0.12, slide: 700)])
        for (i, n) in Sound.scale.enumerated() {
            buffers["gem\(i)"] = render([Note(freq: semis(660, n), dur: 0.12, wave: .sine, vol: 0.25)])
        }
        buffers["near"] = render([Note(freq: 1200, dur: 0.08, wave: .square, vol: 0.08, slide: 1800)])
        buffers["smash"] = render([Note(freq: 180, dur: 0.15, wave: .saw, vol: 0.18, slide: 60)])
        buffers["fever"] = render([0, 4, 7, 12].enumerated().map { i, n in
            Note(freq: semis(523, n), dur: 0.12, wave: .square, vol: 0.12, delay: Double(i) * 0.06)
        })
        buffers["death"] = render([Note(freq: 300, dur: 0.5, wave: .saw, vol: 0.25, slide: 40)])
        buffers["best"] = render([0, 4, 7, 12, 16].enumerated().map { i, n in
            Note(freq: semis(523, n), dur: 0.18, wave: .triangle, vol: 0.18, delay: Double(i) * 0.09)
        })
        buffers["coin"] = render([
            Note(freq: 988, dur: 0.06, wave: .square, vol: 0.08),
            Note(freq: 1319, dur: 0.1, wave: .square, vol: 0.08, delay: 0.06),
        ])
    }

    /// Mixes the notes into one buffer: sample-accurate arpeggios without timers.
    private func render(_ notes: [Note]) -> AVAudioPCMBuffer {
        let rate = format.sampleRate
        let total = notes.map { $0.delay + $0.dur + 0.02 }.max() ?? 0.1
        let frames = AVAudioFrameCount(total * rate)
        let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!
        buf.frameLength = frames
        let out = buf.floatChannelData![0]
        for i in 0..<Int(frames) { out[i] = 0 }
        for note in notes {
            let start = Int(note.delay * rate)
            let count = Int(note.dur * rate)
            var phase = 0.0
            for i in 0..<count where start + i < Int(frames) {
                let k = Double(i) / Double(count)
                let f = note.slide.map { note.freq * pow($0 / note.freq, k) } ?? note.freq
                phase += f / rate
                let x = phase - floor(phase)
                let s: Double
                switch note.wave {
                case .sine: s = sin(2 * .pi * x)
                case .triangle: s = 4 * abs(x - 0.5) - 1
                case .square: s = x < 0.5 ? 1 : -1
                case .saw: s = 2 * x - 1
                }
                // exponential decay like the web version's gain ramp to 0.0001
                let env = note.vol * pow(0.0001 / note.vol, k)
                out[start + i] += Float(s * env)
            }
        }
        return buf
    }

    private func ensureStarted() -> Bool {
        if started && engine.isRunning { return true }
        do {
            try AVAudioSession.sharedInstance().setActive(true)
            try engine.start()
            players.forEach { $0.play() }
            started = true
        } catch {
            started = false
        }
        return started
    }

    private func play(_ name: String) {
        guard enabled, let buf = buffers[name], ensureStarted() else { return }
        let p = players[nextPlayer]
        nextPlayer = (nextPlayer + 1) % players.count
        p.scheduleBuffer(buf, at: nil, options: .interrupts, completionHandler: nil)
        if !p.isPlaying { p.play() }
    }

    func switchRing() { play("switch") }
    /// Pitch climbs with progress towards the next fever, then resets.
    func gem(combo: Int) {
        let i = (combo - 1) % GameConfig.feverEvery
        play("gem\(min(max(i, 0), Sound.scale.count - 1))")
    }
    func nearMiss() { play("near") }
    func smash() { play("smash") }
    func fever() { play("fever") }
    func death() { play("death") }
    func best() { play("best") }
    func coin() { play("coin") }
}
