// Browser smoke test: loads the game, plays a few runs, checks for errors and takes screenshots.
// Usage: node tests/e2e.js [outDir]
const path = require('path');
const fs = require('fs');
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  ({ chromium } = require(path.join(process.execPath, '../../lib/node_modules/playwright')));
}

const outDir = process.argv[2] || path.join(__dirname, '..', 'screenshots');
fs.mkdirSync(outDir, { recursive: true });
const url = 'file://' + path.join(__dirname, '..', 'index.html');

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  for (const vp of [
    { name: 'phone', width: 390, height: 844, isMobile: true, hasTouch: true },
    { name: 'desktop', width: 1280, height: 800 },
  ]) {
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height }, isMobile: vp.isMobile, hasTouch: vp.hasTouch, reducedMotion: 'reduce' });
    page.on('pageerror', (e) => errors.push(vp.name + ': ' + e.message));
    page.on('console', (m) => m.type() === 'error' && errors.push(vp.name + ' console: ' + m.text()));
    await page.goto(url);
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, vp.name + '-menu.png') });

    await page.click('#btn-play');
    await page.waitForTimeout(300);
    if (!(await page.isVisible('#hud'))) errors.push(vp.name + ': HUD not visible after start');
    // tap a few times while playing
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Space');
      await page.waitForTimeout(250);
    }
    await page.screenshot({ path: path.join(outDir, vp.name + '-play.png') });
    // wait for death (idle player dies)
    await page.waitForSelector('#over:not(.hidden)', { timeout: 20000 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, vp.name + '-over.png') });

    await page.click('#btn-home');
    await page.click('#btn-shop');
    await page.screenshot({ path: path.join(outDir, vp.name + '-shop.png') });
    await page.click('#shop .btn-back');
    await page.click('#btn-missions');
    await page.screenshot({ path: path.join(outDir, vp.name + '-missions.png') });
    await page.click('#missions .btn-back');

    // reload: progress must persist
    const plays = await page.evaluate(() => JSON.parse(localStorage.getItem('orbit-switch-save-v1')).plays);
    if (plays !== 1) errors.push(vp.name + ': expected plays=1 after one run, got ' + plays);
    await page.reload();
    const plays2 = await page.evaluate(() => JSON.parse(localStorage.getItem('orbit-switch-save-v1')).plays);
    if (plays2 !== 1) errors.push(vp.name + ': save lost on reload');
    await page.close();
  }

  // Autoplay: the built-in autopilot plays a real run. Checks scoring, pause/resume and frame time.
  {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
    page.on('pageerror', (e) => errors.push('autoplay: ' + e.message));
    await page.goto(url + '?autoplay');
    await page.click('#btn-play');
    await page.waitForTimeout(6000);
    const score1 = Number(await page.textContent('#hud-score'));
    if (!(score1 > 5)) errors.push('autoplay: score did not increase (' + score1 + ')');
    if (await page.isVisible('#over')) errors.push('autoplay: autopilot died within 6s');

    await page.keyboard.press('Escape');
    if (!(await page.isVisible('#pause'))) errors.push('pause: Escape did not pause');
    const paused = await page.textContent('#hud-score');
    await page.waitForTimeout(800);
    if ((await page.textContent('#hud-score')) !== paused) errors.push('pause: score changed while paused');
    await page.click('#btn-resume');
    if (!(await page.isVisible('#hud'))) errors.push('pause: resume failed');

    const frames = await page.evaluate(
      () =>
        new Promise((res) => {
          const ts = [];
          function f(t) {
            ts.push(t);
            if (ts.length < 120) requestAnimationFrame(f);
            else res(ts);
          }
          requestAnimationFrame(f);
        })
    );
    const gaps = frames.slice(1).map((t, i) => t - frames[i]).sort((a, b) => a - b);
    const p95 = gaps[Math.floor(gaps.length * 0.95)];
    console.log('frame time p50 ' + gaps[gaps.length >> 1].toFixed(1) + 'ms, p95 ' + p95.toFixed(1) + 'ms');
    await page.screenshot({ path: path.join(outDir, 'autoplay.png') });
    await page.close();
  }
  await browser.close();
  if (errors.length) {
    console.error('E2E FAIL\n' + errors.join('\n'));
    process.exit(1);
  }
  console.log('E2E OK, screenshots in ' + outDir);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
