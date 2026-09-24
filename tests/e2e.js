// Browser smoke test: loads the game, plays a few runs, checks for errors and takes screenshots.
// Usage: node tests/e2e.js [outDir]
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const http = require('http');

const outDir = process.argv[2] || path.join(__dirname, '..', 'screenshots');
fs.mkdirSync(outDir, { recursive: true });
const root = path.join(__dirname, '..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };

// Serve over HTTP like a real deployment (file:// hides 404s, manifest and service-worker problems).
function serve() {
  const server = http.createServer((req, res) => {
    const p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    const file = path.join(root, p.endsWith('/') ? p + 'index.html' : p);
    if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404);
      return res.end('not found');
    }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)));
}

(async () => {
  const server = await serve();
  const url = 'http://127.0.0.1:' + server.address().port + '/';
  const browser = await chromium.launch();
  const errors = [];
  for (const vp of [
    { name: 'phone', width: 390, height: 844, isMobile: true, hasTouch: true, locale: 'ja-JP' },
    { name: 'desktop', width: 1280, height: 800, locale: 'en-US' },
  ]) {
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height }, isMobile: vp.isMobile, hasTouch: vp.hasTouch, locale: vp.locale, reducedMotion: 'reduce' });
    const hasJapanese = async () => /[\u3040-\u30ff\u4e00-\u9fff]/.test(await page.evaluate(() => document.body.innerText));
    page.on('pageerror', (e) => errors.push(vp.name + ': ' + e.message));
    page.on('console', (m) => m.type() === 'error' && errors.push(vp.name + ' console: ' + m.text()));
    page.on('response', (r) => r.status() >= 400 && errors.push(vp.name + ': HTTP ' + r.status() + ' ' + r.url()));
    await page.goto(url);
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(outDir, vp.name + '-menu.png') });
    // The UI follows the browser language: Japanese for ja-JP, English for everyone else.
    const playText = await page.textContent('#btn-play');
    if (vp.locale === 'ja-JP' ? playText !== 'タップでスタート' : playText !== 'TAP TO PLAY') errors.push(vp.name + ': wrong language on menu: ' + playText);
    if (vp.locale === 'en-US' && (await hasJapanese())) errors.push(vp.name + ': Japanese text visible in English UI');

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
    if (vp.locale === 'en-US' && (await hasJapanese())) errors.push(vp.name + ': Japanese text on English results screen');

    await page.click('#btn-home');
    await page.click('#btn-shop');
    await page.screenshot({ path: path.join(outDir, vp.name + '-shop.png') });
    await page.click('#shop .btn-back');
    await page.click('#btn-missions');
    await page.screenshot({ path: path.join(outDir, vp.name + '-missions.png') });
    await page.click('#missions .btn-back');

    // daily challenge: separate mode label and best
    await page.click('#btn-daily');
    await page.waitForSelector('#over:not(.hidden)', { timeout: 20000 });
    if (!(await page.isVisible('#over-mode'))) errors.push(vp.name + ': daily label missing on results');
    await page.screenshot({ path: path.join(outDir, vp.name + '-daily-over.png') });
    await page.click('#btn-home');
    if (!/BEST|NEW/.test(await page.textContent('#daily-best'))) errors.push(vp.name + ': daily best not shown on menu');

    // shop: grant coins, the badge appears, buying equips the skin and deducts coins
    await page.evaluate(() => {
      const k = 'orbit-switch-save-v1';
      const sv = JSON.parse(localStorage.getItem(k));
      sv.coins = 100;
      localStorage.setItem(k, JSON.stringify(sv));
    });
    await page.reload();
    if (!(await page.$eval('#btn-shop', (b) => b.classList.contains('badge')))) errors.push(vp.name + ': shop badge missing with 100 coins');
    await page.click('#btn-shop');
    await page.click('.skin[data-id="lime"]'); // too expensive
    if (!/足りません|Not enough/.test(await page.textContent('#shop-msg'))) errors.push(vp.name + ': no feedback for unaffordable skin');
    await page.click('.skin[data-id="sakura"]');
    const after = await page.evaluate(() => JSON.parse(localStorage.getItem('orbit-switch-save-v1')));
    if (after.skin !== 'sakura' || after.coins !== 20) errors.push(vp.name + ': purchase failed ' + JSON.stringify({ skin: after.skin, coins: after.coins }));
    await page.screenshot({ path: path.join(outDir, vp.name + '-shop-bought.png') });
    await page.click('#shop .btn-back');

    // language toggle: switches immediately and is remembered across reloads
    const langBefore = await page.textContent('#btn-play');
    await page.click('#btn-lang');
    const langAfter = await page.textContent('#btn-play');
    if (langAfter === langBefore) errors.push(vp.name + ': language toggle did nothing');
    await page.screenshot({ path: path.join(outDir, vp.name + '-menu-toggled.png') });
    await page.reload();
    if ((await page.textContent('#btn-play')) !== langAfter) errors.push(vp.name + ': language choice not remembered');

    // reload: progress must persist
    const plays = await page.evaluate(() => JSON.parse(localStorage.getItem('orbit-switch-save-v1')).plays);
    if (plays !== 2) errors.push(vp.name + ': expected plays=2 after two runs, got ' + plays);
    await page.reload();
    const plays2 = await page.evaluate(() => JSON.parse(localStorage.getItem('orbit-switch-save-v1')).plays);
    if (plays2 !== 2) errors.push(vp.name + ': save lost on reload');
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
  // Offline: after one online visit the service worker must be able to serve the whole game.
  {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push('offline: ' + e.message));
    await page.goto(url);
    await page.evaluate(() => navigator.serviceWorker.ready);
    await page.reload(); // now controlled by the service worker
    await context.setOffline(true);
    await page.reload();
    if (!(await page.isVisible('#btn-play'))) errors.push('offline: menu did not load offline');
    await page.click('#btn-play');
    await page.waitForTimeout(300);
    if (!(await page.isVisible('#hud'))) errors.push('offline: game did not start offline');
    await context.close();
  }

  await browser.close();
  server.close();
  if (errors.length) {
    console.error('E2E FAIL\n' + errors.join('\n'));
    process.exit(1);
  }
  console.log('E2E OK, screenshots in ' + outDir);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
