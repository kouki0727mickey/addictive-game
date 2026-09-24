/* ORBIT SWITCH — rendering, input and UI glue. */
(function () {
  'use strict';

  const Core = window.OrbitCore;
  const Meta = window.OrbitMeta;
  const Sfx = window.Sfx;
  const I18n = window.OrbitI18n;
  const C = Core.CONFIG;

  const canvas = document.getElementById('game');
  const ctx = canvas.getContext('2d');
  const $ = (id) => document.getElementById(id);

  let W = 0;
  let H = 0;
  let DPR = 1;
  let unit = 1; // pixels per world unit
  let CX = 0; // screen position of the orbit centre
  let CY = 0;
  const HUD_H = 96; // px reserved at the top for the score

  // Accessing window.localStorage itself can throw (sandboxed iframes, blocked cookies).
  const storage = (function () {
    try {
      const s = window.localStorage;
      s.getItem('probe');
      return s;
    } catch (e) {
      return null;
    }
  })();
  const save = Meta.load(storage);

  // ---------- language ----------
  let lang = 'en';
  let T = I18n.create(lang);
  function setLanguage() {
    lang = I18n.resolve(save.lang, navigator.languages || [navigator.language]);
    T = I18n.create(lang);
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach((el) => (el.textContent = T(el.dataset.i18n)));
    document.querySelectorAll('[data-i18n-html]').forEach((el) => (el.innerHTML = T(el.dataset.i18nHtml))); // our own constant strings
    document.querySelectorAll('[data-i18n-aria]').forEach((el) => el.setAttribute('aria-label', T(el.dataset.i18nAria)));
    $('btn-lang').textContent = lang === 'ja' ? 'EN' : 'JA';
  }
  setLanguage();
  const missionText = (m) => T('mission.' + m.kind, { n: m.goal });
  const skinName = (s) => T('skin.' + s.id);
  Sfx.setMuted(save.muted);
  const dailyBonus = Meta.checkDaily(save, Date.now());
  Meta.persist(storage, save);

  let state = 'menu'; // menu | play | over | shop | missions
  let game = Core.createGame(Date.now());
  let particles = [];
  let texts = [];
  let shake = 0;
  let flash = 0;
  let trail = [];
  let deathTimer = 0;
  let hitStop = 0; // seconds of frozen time (impact feel)
  let slowMo = 0; // seconds of slow motion remaining
  let readyTimer = 0; // seconds of "READY" freeze after resuming from pause
  let hue = 0;
  // Test hook: ?autoplay lets the built-in autopilot play real runs (used by the E2E test).
  const REDUCED_MOTION = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const AUTOPLAY = /[?&]autoplay\b/.test(window.location.search);
  let retryLockUntil = 0; // prevents a panic-tap at death from skipping the results

  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.floor(W * DPR);
    canvas.height = Math.floor(H * DPR);
    // The outer ring plus player needs ~0.9 units of diameter. Fit that between the HUD and the bottom edge.
    const availH = H - HUD_H - 8;
    unit = Math.min(W / 0.95, availH / 0.9, Math.min(W, H));
    CX = W / 2;
    CY = HUD_H + availH / 2;
  }
  window.addEventListener('resize', resize);
  resize();

  function skin() {
    return Meta.SKINS.find((s) => s.id === save.skin) || Meta.SKINS[0];
  }

  function skinColor(which) {
    const c = skin()[which];
    return c === 'rainbow' ? 'hsl(' + (hue % 360) + ',100%,65%)' : c;
  }

  // ---------- screens ----------
  function show(name) {
    ['menu', 'over', 'shop', 'missions', 'pause'].forEach((id) => $(id).classList.toggle('hidden', id !== name));
    $('hud').classList.toggle('hidden', name !== 'play' && name !== 'pause');
    state = name;
  }

  function renderMenu() {
    $('menu-best').textContent = save.best;
    $('menu-coins').textContent = save.coins;
    const lp = Meta.levelProgress(save.xp);
    $('menu-level').textContent = lp.level;
    $('menu-xp').style.width = Math.round((lp.into / lp.need) * 100) + '%';
    $('btn-mute').textContent = save.muted ? '🔇' : '🔊';
    // A badge pulls players into the shop the moment they can afford something.
    const canBuy = Meta.SKINS.some((s) => save.owned.indexOf(s.id) === -1 && save.coins >= s.price);
    $('btn-shop').classList.toggle('badge', canBuy);
    const db = Meta.dailyBest(save, Meta.today(Date.now()));
    $('daily-best').textContent = db > 0 ? 'BEST ' + db : T('menu.new');
  }

  function esc(v) {
    return String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  }

  function missionHtml(m, done) {
    const pct = Math.min(100, Math.round((m.progress / m.goal) * 100));
    return (
      '<div class="mission' + (done ? ' done' : '') + '">' +
      '<span class="reward">🪙' + esc(m.reward) + '</span>' +
      (done ? '✅ ' : '') + esc(missionText(m)) +
      ' <small>(' + esc(Math.min(m.progress, m.goal)) + '/' + esc(m.goal) + ')</small>' +
      '<div class="bar"><i style="width:' + pct + '%"></i></div></div>'
    );
  }

  function renderMissions() {
    $('mission-list').innerHTML = save.missions.map((m) => missionHtml(m, false)).join('');
    $('lifetime').textContent = T('missions.lifetime', { plays: save.plays, gems: save.totalGems, level: Meta.levelFromXp(save.xp) });
  }

  function renderShop() {
    $('shop-coins').textContent = save.coins;
    $('shop-msg').textContent = '';
    $('shop-list').innerHTML = Meta.SKINS.map((s) => {
      const owned = save.owned.indexOf(s.id) !== -1;
      const affordable = !owned && save.coins >= s.price;
      const bg = s.color === 'rainbow' ? 'conic-gradient(red,orange,yellow,lime,cyan,blue,magenta,red)' : s.color;
      return (
        '<button class="skin' + (save.skin === s.id ? ' selected' : '') + (owned ? '' : affordable ? ' affordable' : ' locked') + '" data-id="' + s.id + '" aria-pressed="' + (save.skin === s.id) + '">' +
        '<span class="dot" style="background:' + bg + '"></span>' + esc(skinName(s)) +
        '<small>' + (owned ? T(save.skin === s.id ? 'shop.equipped' : 'shop.owned') : (affordable ? T('shop.buy') + ' ' : '') + '🪙' + s.price) + '</small></button>'
      );
    }).join('');
  }

  $('shop-list').addEventListener('click', (e) => {
    const b = e.target.closest('.skin');
    if (!b) return;
    const id = b.dataset.id;
    if (Meta.buySkin(save, id)) {
      Sfx.coin();
      Meta.persist(storage, save);
      renderShop();
    } else {
      const skinDef = Meta.SKINS.find((s) => s.id === id);
      $('shop-msg').textContent = T('shop.notEnough', { n: skinDef.price - save.coins });
      b.classList.remove('nope');
      void b.offsetWidth;
      b.classList.add('nope');
    }
  });

  // ---------- game flow ----------
  let mode = 'normal'; // normal | daily
  // Captured when a run starts: a daily run that crosses midnight still belongs to the day
  // (and stage) it started on, and the HUD doesn't rebuild a date string every frame.
  let runDay = '';
  let runBest = 0;

  function startGame(nextMode) {
    if (nextMode === 'normal' || nextMode === 'daily') mode = nextMode;
    Sfx.unlock();
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    runDay = Meta.today(Date.now());
    runBest = mode === 'daily' ? Meta.dailyBest(save, runDay) : save.best;
    const seed = mode === 'daily' ? Meta.dailySeed(runDay) : (Date.now() ^ (Math.random() * 1e9)) >>> 0;
    game = Core.createGame(seed);
    particles = [];
    texts = [];
    trail = [];
    shake = 0;
    flash = 0;
    deathTimer = 0;
    hitStop = 0;
    slowMo = 0;
    readyTimer = 0;
    missionsAnnounced = [];
    show('play');
    hudCache.score = -1;
    hudCache.mult = hudCache.fever = hudCache.best = null;
    updateHud();
  }

  function endGame() {
    const run = {
      score: game.score,
      gems: game.gems,
      nearMisses: game.nearMisses,
      bestCombo: game.bestCombo,
      feverCount: game.feverCount,
    };
    const sum = Meta.applyRun(save, run);
    // In daily mode, "best" means today's challenge best.
    const rec = mode === 'daily' ? Meta.recordDaily(save, runDay, run.score) : { prevBest: sum.prevBest, best: save.best, newBest: sum.newBest };
    Meta.persist(storage, save);

    $('over-mode').classList.toggle('hidden', mode !== 'daily');
    $('over-score').textContent = run.score;
    $('over-best').textContent = rec.best + (mode === 'daily' ? T('over.try', { n: save.daily.tries }) : '');
    $('over-newbest').classList.toggle('hidden', !rec.newBest);
    const gap = rec.best - run.score;
    let tease;
    if (rec.newBest) tease = T('over.tease.newBest', { n: run.score - rec.prevBest });
    else if (rec.best === 0) tease = T('over.tease.zero');
    else if (rec.prevBest === 0 && run.score > 0) tease = T('over.tease.first');
    else if (gap === 0) tease = T('over.tease.tied');
    else if (gap <= 5) tease = T('over.tease.close', { n: gap + 1 });
    else tease = T('over.tease.far', { n: gap + 1 });
    $('over-tease').textContent = tease;
    $('over-details').innerHTML =
      '<li>' + T('over.gems') + ' <b>' + run.gems + '</b></li>' +
      '<li>' + T('over.bestCombo') + ' <b>' + run.bestCombo + '</b></li>' +
      '<li>' + T('over.nearMisses') + ' <b>' + run.nearMisses + '</b></li>' +
      (game.smashed ? '<li>' + T('over.smashed') + ' <b>' + game.smashed + '</b></li>' : '') +
      '<li>🪙 <b id="over-coins">+0</b></li>' +
      (sum.levelUps ? '<li>' + T('over.levelUp') + ' <b>Lv' + Meta.levelFromXp(save.xp) + '</b></li>' : '');
    const next = Meta.SKINS.filter((s) => save.owned.indexOf(s.id) === -1).sort((a, b) => a.price - b.price)[0];
    $('over-unlock').textContent = !next
      ? ''
      : save.coins >= next.price
        ? T('over.canUnlock', { name: skinName(next) })
        : T('over.nextUnlock', { name: skinName(next), n: next.price - save.coins });
    $('over-missions').innerHTML =
      sum.completed.map((m) => missionHtml(m, true)).join('') + save.missions.map((m) => missionHtml(m, false)).join('');
    show('over');
    retryLockUntil = performance.now() + 600;
    countUp($('over-coins'), sum.coins);
    if (rec.newBest) Sfx.best();
    else if (sum.completed.length || sum.levelUps) Sfx.coin();
    if (rec.newBest || sum.completed.length) buzz([15, 30, 15]);
  }

  // Rewards feel bigger when you watch them tick up.
  function countUp(el, target) {
    const start = performance.now();
    const dur = Math.min(900, 200 + target * 12);
    (function tick(now) {
      const k = Math.min(1, (now - start) / dur);
      el.textContent = '+' + Math.round(target * (1 - Math.pow(1 - k, 3)));
      if (k < 1 && state === 'over') requestAnimationFrame(tick);
      else el.textContent = '+' + target;
    })(start);
  }

  // Sharing a score is how friends find the game: Web Share on mobile, clipboard elsewhere.
  function shareScore() {
    const score = Number($('over-score').textContent) || 0;
    const url = /^https?:/.test(window.location.protocol) ? window.location.origin + window.location.pathname : '';
    const text =
      mode === 'daily'
        ? T('share.daily', { day: runDay, score })
        : T('share.normal', { score, best: save.best });
    const toast = (msg) => {
      const t = $('share-toast');
      t.textContent = msg;
      t.classList.remove('hidden');
      clearTimeout(toast.timer);
      toast.timer = setTimeout(() => t.classList.add('hidden'), 1800);
    };
    if (navigator.share) {
      navigator.share({ title: 'ORBIT SWITCH', text, url: url || undefined }).catch(() => {});
    } else if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url ? text + ' ' + url : text).then(
        () => toast(T('share.copied')),
        () => toast(T('share.failed'))
      );
    } else {
      toast(text);
    }
  }

  function buzz(pattern) {
    if (save.muted || !navigator.vibrate) return;
    try {
      navigator.vibrate(pattern);
    } catch (e) {
      /* some browsers throw when not triggered by a gesture */
    }
  }

  function onTap() {
    if (state === 'play' && readyTimer <= 0) {
      Core.switchRing(game);
    }
  }

  // ---------- input ----------
  canvas.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    onTap();
  });
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Escape' || e.code === 'KeyP') {
      if (state === 'play') pause();
      else if (state === 'pause') resume();
      return;
    }
    if (e.code === 'Space' || e.code === 'ArrowUp' || e.code === 'ArrowDown' || e.code === 'Enter') {
      // Let focused buttons handle Space/Enter themselves in menus.
      if (state !== 'play' && e.target.closest && e.target.closest('button')) return;
      e.preventDefault();
      if (e.repeat) return;
      if (state === 'play') onTap();
      else if (state === 'menu') startGame('normal');
      else if (state === 'over' && performance.now() > retryLockUntil) startGame();
      else if (state === 'pause') resume();
    }
  });

  function pause() {
    if (state === 'play' && game.alive) show('pause');
  }
  function resume() {
    if (state !== 'pause') return;
    last = performance.now();
    readyTimer = 0.8; // short countdown so the player can re-orient before time moves
    show('play');
  }
  function showDaily(bonus) {
    if (bonus <= 0) return;
    const d = $('daily');
    showDaily.last = bonus;
    d.textContent = T('menu.dailyBonus', { bonus, streak: save.streak });
    d.classList.remove('hidden');
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return pause();
    // An installed PWA can stay open for days: re-check the daily bonus when we come back.
    const bonus = Meta.checkDaily(save, Date.now());
    if (bonus > 0) {
      Meta.persist(storage, save);
      showDaily(bonus);
      if (state === 'menu') renderMenu();
    }
  });
  window.addEventListener('blur', pause);
  $('pause').addEventListener('pointerdown', (e) => {
    e.preventDefault();
    resume();
  });

  $('btn-play').addEventListener('click', () => startGame('normal'));
  $('btn-daily').addEventListener('click', () => startGame('daily'));
  $('btn-retry').addEventListener('click', () => {
    if (performance.now() > retryLockUntil) startGame();
  });
  // Tapping empty space on the menu / results starts a run: one less step between tries.
  ['menu', 'over'].forEach((id) =>
    $(id).addEventListener('pointerdown', (e) => {
      if (e.target.closest('button, .missions, .toast')) return;
      if (id === 'over' && performance.now() < retryLockUntil) return;
      e.preventDefault();
      startGame(id === 'menu' ? 'normal' : undefined);
    })
  );
  $('btn-share').addEventListener('click', shareScore);
  $('btn-home').addEventListener('click', () => {
    renderMenu();
    show('menu');
  });
  $('btn-shop').addEventListener('click', () => {
    renderShop();
    show('shop');
  });
  $('btn-missions').addEventListener('click', () => {
    renderMissions();
    show('missions');
  });
  document.querySelectorAll('.btn-back').forEach((b) =>
    b.addEventListener('click', () => {
      renderMenu();
      show('menu');
    })
  );
  // Switches the explicit language choice; the default ('auto') follows the device language.
  $('btn-lang').addEventListener('click', () => {
    save.lang = lang === 'ja' ? 'en' : 'ja';
    Meta.persist(storage, save);
    setLanguage();
    if (showDaily.last) showDaily(showDaily.last);
    renderMenu();
  });
  $('btn-mute').addEventListener('click', () => {
    save.muted = !save.muted;
    Sfx.setMuted(save.muted);
    Meta.persist(storage, save);
    renderMenu();
  });

  // ---------- effects ----------
  function burst(x, y, color, n, speed) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const v = (0.2 + Math.random()) * speed;
      particles.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: 0.6 + Math.random() * 0.4, color });
    }
  }

  function popText(x, y, text, color, size) {
    texts.push({ x, y, text, color, size: size || 22, life: 0.9 });
  }

  function handleEvents() {
    for (const e of Core.drainEvents(game)) {
      switch (e.type) {
        case 'switch':
          Sfx.switch();
          break;
        case 'gem':
          Sfx.gem(e.combo, C.feverEvery);
          burst(e.x, e.y, '#ffc94d', 10, 0.35);
          popText(e.x, e.y, '+' + e.points, '#ffc94d');
          break;
        case 'nearMiss':
          Sfx.nearMiss();
          slowMo = 0.12;
          buzz(8);
          popText(e.x, e.y, 'CLOSE!', '#4df3ff', 20);
          break;
        case 'smash':
          Sfx.smash();
          shake = Math.max(shake, 6);
          burst(e.x, e.y, '#ff4d6d', 14, 0.5);
          break;
        case 'fever':
          Sfx.fever();
          buzz([20, 40, 20]);
          flash = 0.5;
          popText(0, 0, 'FEVER!!', '#ff7ad9', 44);
          break;
        case 'feverEnd':
          popText(0, 0, 'FEVER END', '#ff7ad9', 24);
          break;
        case 'comboLost':
          if (e.combo >= 3) popText(0, 0.06, 'combo lost', '#8a90b8', 18);
          break;
        case 'death':
          Sfx.death();
          buzz(80);
          shake = 16;
          flash = 0.6;
          burst(e.x, e.y, skinColor('color'), 40, 0.7);
          deathTimer = 0.9;
          hitStop = 0.12;
          break;
      }
    }
  }

  // ---------- rendering ----------
  function toScreen(x, y) {
    return [CX + x * unit, CY + y * unit];
  }

  const bgCache = { key: '', grad: null };
  function drawBackground(t) {
    const fever = game.fever > 0;
    const key = (fever ? 'f' : 'n') + W + 'x' + H;
    if (bgCache.key !== key) {
      const g = ctx.createRadialGradient(CX, CY, 0, CX, CY, Math.max(W, H) * 0.7);
      g.addColorStop(0, fever ? '#2a0b3a' : '#10123a');
      g.addColorStop(1, '#07071a');
      bgCache.key = key;
      bgCache.grad = g;
    }
    ctx.fillStyle = bgCache.grad;
    ctx.fillRect(0, 0, W, H);

    // pulsing rings
    for (let i = 0; i < 2; i++) {
      const [cx, cy] = toScreen(0, 0);
      const r = C.ringRadius[i] * unit;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = fever ? 'rgba(255,122,217,0.55)' : 'rgba(120,140,255,0.35)';
      ctx.lineWidth = 2 + Math.sin(t * 4 + i) * 0.8;
      ctx.stroke();
    }
    // centre core
    const [cx, cy] = toScreen(0, 0);
    const pr = 0.07 * unit * (1 + Math.sin(t * 6) * 0.04);
    ctx.beginPath();
    ctx.arc(cx, cy, pr, 0, Math.PI * 2);
    ctx.fillStyle = fever ? 'rgba(255,122,217,0.25)' : 'rgba(77,243,255,0.12)';
    ctx.fill();
  }

  // shadowBlur is very slow on mobile canvases, so glowing shapes are pre-rendered once per size/colour.
  const spriteCache = new Map();
  function sprite(key, radius, paint) {
    const k = key + '@' + Math.round(radius * DPR * 10);
    let c = spriteCache.get(k);
    if (!c) {
      if (spriteCache.size > 24) spriteCache.clear(); // window resizes create new sizes; don't grow forever
      const pad = 16;
      const size = Math.ceil((radius * 2.6 + pad * 2) * DPR);
      c = document.createElement('canvas');
      c.width = c.height = size;
      const g = c.getContext('2d');
      g.scale(DPR, DPR);
      g.translate(size / DPR / 2, size / DPR / 2);
      paint(g, radius);
      c.half = size / DPR / 2;
      spriteCache.set(k, c);
    }
    return c;
  }

  function paintSpike(color) {
    return (g, r) => {
      g.beginPath();
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        const rr = i % 2 ? r * 0.55 : r * 1.25;
        g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
      }
      g.closePath();
      g.fillStyle = color;
      g.shadowColor = '#ff4d6d';
      g.shadowBlur = 12;
      g.fill();
    };
  }

  function paintGem(g, r) {
    g.rotate(Math.PI / 4);
    g.fillStyle = '#ffc94d';
    g.shadowColor = '#ffc94d';
    g.shadowBlur = 14;
    g.fillRect(-r * 0.7, -r * 0.7, r * 1.4, r * 1.4);
  }

  function drawSprite(img, x, y, rotation, scale) {
    const [sx, sy] = toScreen(x, y);
    const h = img.half * (scale || 1);
    if (rotation) {
      ctx.save();
      ctx.translate(sx, sy);
      ctx.rotate(rotation);
      ctx.drawImage(img, -h, -h, h * 2, h * 2);
      ctx.restore();
    } else {
      ctx.drawImage(img, sx - h, sy - h, h * 2, h * 2);
    }
  }

  function drawSpike(x, y, angle) {
    const fever = game.fever > 0;
    const img = sprite(fever ? 'spikeF' : 'spike', C.spikeRadius * unit, paintSpike(fever ? '#ff9ec0' : '#ff4d6d'));
    drawSprite(img, x, y, angle, 1);
  }

  function drawGem(x, y, t) {
    drawSprite(sprite('gem', C.gemRadius * unit, paintGem), x, y, 0, 1 + Math.sin(t * 8) * 0.12);
  }

  function drawPlayer() {
    // Blink while invulnerable after fever, and flicker in the last second of fever as a warning.
    const warn = game.grace > 0 || (game.fever > 0 && game.fever < 1);
    if (warn && Math.floor(game.t * 14) % 2 === 0) return;
    const p = Core.playerPos(game);
    // Trail length is measured in game time, so it looks the same at 60Hz and 120Hz.
    const TRAIL_T = 0.2;
    if (!trail.length || trail[trail.length - 1].t !== game.t) trail.push({ x: p.x, y: p.y, t: game.t });
    while (trail.length && game.t - trail[0].t > TRAIL_T) trail.shift();
    const base = ctx.globalAlpha;
    ctx.save();
    // Tapered ribbon: consecutive segments get thicker and more opaque towards the player.
    ctx.strokeStyle = skinColor('trail');
    ctx.lineCap = 'round';
    for (let i = 1; i < trail.length; i++) {
      const k = 1 - (game.t - trail[i].t) / TRAIL_T;
      const [ax, ay] = toScreen(trail[i - 1].x, trail[i - 1].y);
      const [bx, by] = toScreen(trail[i].x, trail[i].y);
      ctx.globalAlpha = base * k * 0.6;
      ctx.lineWidth = C.playerRadius * unit * 2 * k;
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.stroke();
    }
    ctx.globalAlpha = base;
    const [sx, sy] = toScreen(p.x, p.y);
    ctx.beginPath();
    ctx.arc(sx, sy, C.playerRadius * unit, 0, Math.PI * 2);
    ctx.fillStyle = game.fever > 0 ? '#fff' : skinColor('color');
    ctx.shadowColor = skinColor('color');
    ctx.shadowBlur = 20;
    ctx.fill();
    ctx.restore();
  }

  // First runs only: flash "TAP!" when a spike is coming on the player's ring and the other ring is clear.
  function drawTutorial(t) {
    let cur = Infinity;
    let other = Infinity;
    for (const o of game.objects) {
      if (o.type !== 'spike') continue;
      const rel = o.angle - game.angle;
      if (rel < 0) continue;
      if (o.ring === game.ring) cur = Math.min(cur, rel);
      else other = Math.min(other, rel);
    }
    const danger = cur < 0.9 && other > cur + 0.15;
    // The centre of the orbit is always empty, so hints never collide with popups.
    const [sx, sy] = toScreen(0, 0);
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    if (danger) {
      ctx.font = '900 ' + Math.round(26 + Math.sin(t * 18) * 3) + 'px system-ui, sans-serif';
      ctx.fillStyle = '#fff';
      ctx.shadowColor = '#4df3ff';
      ctx.shadowBlur = 16;
      ctx.fillText('TAP!', sx, sy);
    } else if (game.passedSpikes === 0) {
      ctx.font = '700 15px system-ui, sans-serif';
      ctx.fillStyle = 'rgba(238,242,255,0.8)';
      const [l1, l2] = T('hint.start').split('\n');
      ctx.fillText(l1, sx, sy - 10);
      ctx.fillText(l2 || '', sx, sy + 10);
    }
    ctx.restore();
  }

  function drawEffects(dt) {
    for (const p of particles) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vx *= 0.92;
      p.vy *= 0.92;
      p.life -= dt;
      const [sx, sy] = toScreen(p.x, p.y);
      ctx.globalAlpha = Math.max(0, p.life);
      ctx.fillStyle = p.color;
      ctx.fillRect(sx - 2, sy - 2, 4, 4);
    }
    particles = particles.filter((p) => p.life > 0);

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (const tx of texts) {
      tx.life -= dt;
      tx.y -= dt * 0.08;
      let [sx, sy] = toScreen(tx.x, tx.y);
      ctx.globalAlpha = Math.max(0, Math.min(1, tx.life * 2));
      ctx.font = '800 ' + tx.size + 'px system-ui, sans-serif';
      const half = ctx.measureText(tx.text).width / 2 + 8;
      sx = Math.min(W - half, Math.max(half, sx));
      sy = Math.min(H - tx.size, Math.max(tx.size, sy));
      ctx.fillStyle = tx.color;
      ctx.fillText(tx.text, sx, sy);
    }
    texts = texts.filter((t) => t.life > 0);
    ctx.globalAlpha = 1;
  }

  // DOM writes are relatively expensive: only touch the HUD when something changed.
  const hudCache = { score: -1, mult: '', fever: '', best: '' };
  // Tell the player the moment a mission is done instead of waiting for the results screen.
  let missionsAnnounced = [];
  function checkMissionsLive() {
    for (const m of save.missions) {
      if (m.cumulative || missionsAnnounced.indexOf(m) !== -1) continue;
      if ((game[m.kind] || 0) >= m.goal) {
        missionsAnnounced.push(m);
        popText(0, 0.1, '✅ ' + missionText(m), '#ffc94d', 18);
        Sfx.coin();
      }
    }
  }

  function updateHud() {
    checkMissionsLive();
    // Chasing your best is the core hook: show it, and celebrate the moment you pass it.
    const best = runBest;
    const beaten = best > 0 && game.score > best;
    const bestText = best === 0 ? '' : beaten ? 'NEW BEST!' : (mode === 'daily' ? '📅 BEST ' : 'BEST ') + best;
    if (bestText !== hudCache.best) {
      const el = $('hud-best');
      el.textContent = bestText;
      el.classList.toggle('beaten', beaten);
      if (beaten && hudCache.best && hudCache.best !== 'NEW BEST!') {
        popText(0, -0.08, 'NEW BEST!', '#ffc94d', 30);
        Sfx.coin();
        buzz(20);
      }
      hudCache.best = bestText;
    }
    if (game.score !== hudCache.score) {
      const el = $('hud-score');
      el.textContent = game.score;
      if (game.score > hudCache.score && hudCache.score >= 0) {
        el.classList.remove('bump');
        void el.offsetWidth; // restart the CSS animation
        el.classList.add('bump');
      }
      hudCache.score = game.score;
    }
    const m = Core.multiplier(game) * (game.fever > 0 ? 2 : 1);
    const multText = m > 1 ? '×' + m + (game.fever > 0 ? ' FEVER' : '') : game.combo >= 2 ? T('hud.combo', { n: game.combo }) : '';
    if (multText !== hudCache.mult) {
      $('hud-mult').textContent = multText;
      hudCache.mult = multText;
    }
    const on = game.fever > 0;
    const pct = on ? (game.fever / C.feverDuration) * 100 : ((game.combo % C.feverEvery) / C.feverEvery) * 100;
    const feverKey = (on ? 'on' : 'off') + Math.round(pct);
    if (feverKey !== hudCache.fever) {
      const meter = $('hud-fever');
      meter.classList.toggle('on', on);
      meter.firstElementChild.style.width = pct + '%';
      hudCache.fever = feverKey;
    }
  }

  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    hue += dt * 120;

    const demoMode = state === 'menu' || state === 'shop' || state === 'missions';
    if (demoMode) {
      // Attract mode: the autopilot plays quietly behind the menus.
      if (!game.demo || !game.alive) {
        game = Core.createGame((Math.random() * 1e9) >>> 0);
        game.demo = true;
        trail = [];
      }
      if (Core.autopilot(game)) Core.switchRing(game);
      Core.step(game, dt);
      Core.drainEvents(game);
    }

    if (state === 'play') {
      if (AUTOPLAY && Core.autopilot(game)) Core.switchRing(game);
      if (readyTimer > 0) {
        readyTimer -= dt;
      } else if (hitStop > 0) {
        hitStop -= dt;
      } else if (game.alive) {
        let scale = 1;
        if (slowMo > 0) {
          slowMo -= dt;
          scale = 0.45;
        }
        Core.step(game, dt * scale);
      } else {
        deathTimer -= dt;
        if (deathTimer <= 0) endGame();
      }
      handleEvents();
      updateHud();
    }

    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.save();
    if (REDUCED_MOTION) shake = flash = 0; // no screen shake or white flashes for motion-sensitive players
    if (shake > 0) {
      ctx.translate((Math.random() - 0.5) * shake, (Math.random() - 0.5) * shake);
      shake = Math.max(0, shake - dt * 40);
    }
    drawBackground(now / 1000);
    {
      ctx.globalAlpha = demoMode ? 0.35 : 1;
      for (const o of game.objects) {
        const q = Core.objectPos(o);
        if (o.type === 'spike') drawSpike(q.x, q.y, o.angle);
        else drawGem(q.x, q.y, now / 1000);
      }
      if (game.alive) drawPlayer();
      ctx.globalAlpha = 1;
      if (state === 'play' && game.alive && save.plays < 3 && game.passedSpikes < 4) drawTutorial(now / 1000);
      if (state === 'play' && readyTimer > 0) {
        const [sx, sy] = toScreen(0, 0);
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = '900 30px system-ui, sans-serif';
        ctx.fillStyle = '#fff';
        ctx.fillText('READY', sx, sy);
        ctx.restore();
      }
    }
    drawEffects(dt);
    ctx.restore();

    if (flash > 0) {
      ctx.fillStyle = 'rgba(255,255,255,' + flash * 0.6 + ')';
      ctx.fillRect(0, 0, W, H);
      flash = Math.max(0, flash - dt * 2);
    }
    requestAnimationFrame(frame);
  }

  // Offline support (only meaningful when served over http/https).
  if ('serviceWorker' in navigator && /^https?:/.test(window.location.protocol)) {
    window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
  }

  renderMenu();
  showDaily(dailyBonus);
  show('menu');
  requestAnimationFrame(frame);
})();
