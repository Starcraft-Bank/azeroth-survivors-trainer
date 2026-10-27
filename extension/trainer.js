/* The patcher is also exercised under Node by test_patch.cjs. */
(() => {
  'use strict';
  const spec = globalThis.AZS_PATCH_SPEC;
  const hex = s => Uint8Array.from(s.match(/../g) || [], b => parseInt(b, 16));
  const concat = parts => {
    const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
    let at = 0;
    for (const part of parts) { out.set(part, at); at += part.length; }
    return out;
  };
  const bytes = (...parts) => concat(parts);
  const leb = n => {
    const out = [];
    do { const b = n & 127; n = Math.floor(n / 128); out.push(b | (n ? 128 : 0)); } while (n);
    return Uint8Array.from(out);
  };
  const read = (b, p) => {
    let n = 0, shift = 0, c;
    do { c = b[p++]; n += (c & 127) * 2 ** shift; shift += 7; } while (c & 128);
    return [n, p];
  };
  const section = (id, body) => bytes(Uint8Array.of(id), leb(body.length), body);
  const hash = async b => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', b)),
    n => n.toString(16).padStart(2, '0')).join('');
  const exportEntry = (name, kind, index) => {
    const s = new TextEncoder().encode(name);
    return bytes(leb(s.length), s, Uint8Array.of(kind), leb(index));
  };

  async function patch(input, testExports = false) {
    const b = input instanceof Uint8Array ? input : new Uint8Array(input);
    if (b.length !== spec.bytes || await hash(b) !== spec.sha256) {
      throw new Error('Unsupported game build. No patch applied; this trainer needs updating.');
    }
    const output = [b.subarray(0, 8)];
    let p = 8, imports = 0;
    while (p < b.length) {
      const id = b[p], [length, start] = read(b, p + 1), end = start + length;
      let body = b.subarray(start, end);
      if (id === 2) {
        // WASM-bindgen's exact-build imports are all functions; verify, do not assume silently.
        let [n, q] = read(body, 0);
        for (let i = 0; i < n; i++) {
          let len; [len, q] = read(body, q); q += len;
          [len, q] = read(body, q); q += len;
          if (body[q++] !== 0) throw new Error('Unexpected non-function import.');
          [, q] = read(body, q); imports++;
        }
      } else if (id === 3) {
        const additions = spec.additionalFunctions || [];
        if (additions.length) {
          const [n, q] = read(body, 0);
          body = bytes(leb(n + additions.length), body.subarray(q), ...additions.map(f => leb(f.type)));
        }
      } else if (id === 6) {
        const [n, q] = read(body, 0);
        if (n !== spec.globalCount) throw new Error('Global layout mismatch.');
        body = bytes(leb(n + Object.keys(spec.globals).length), body.subarray(q), hex(spec.globalEntries));
      } else if (id === 7) {
        const [n, q] = read(body, 0);
        const extra = Object.entries(spec.globals).map(([name, index]) =>
          exportEntry('__azs_' + name, 3, index));
        for (const f of spec.additionalFunctions || []) if (f.export) extra.push(exportEntry(f.export, 0, f.index));
        if (testExports) {
          extra.push(exportEntry('__azs_test_hurt', 0, 1239));
          extra.push(exportEntry('__azs_test_cast', 0, 927));
          extra.push(exportEntry('__azs_test_live_cast', 0, 1979));
          extra.push(exportEntry('__azs_test_reroll', 0, 20355));
          extra.push(exportEntry('__azs_test_chest', 0, 20954));
          extra.push(exportEntry('__azs_test_gold_pickup', 0, 28509));
          extra.push(exportEntry('__azs_test_xp_gain', 0, 3235));
          extra.push(exportEntry('__azs_test_choice', 0, 1462));
          extra.push(exportEntry('__azs_test_mob_spawn', 0, 5719));
          extra.push(exportEntry('__azs_test_serialize', 0, 1048));
          extra.push(exportEntry('__azs_test_unseal', 0, 27319));
          extra.push(exportEntry('__azs_test_allocate', 0, 106160));
        }
        body = bytes(leb(n + extra.length), body.subarray(q), ...extra);
      } else if (id === 10) {
        const [n, q] = read(body, 0);
        let at = q;
        const parts = [leb(n + (spec.additionalFunctions || []).length)];
        for (let i = 0; i < n; i++) {
          const [size, begin] = read(body, at);
          const edits = spec.edits.filter(e => e.function === i + imports);
          let fn = body.subarray(begin, begin + size);
          if (edits.length) {
            if (await hash(fn) !== spec.bodyHashes[i + imports]) throw new Error('Function mismatch.');
            for (const edit of edits.sort((a, b) => b.offset - a.offset)) {
              const before = hex(edit.before), after = hex(edit.after);
              if (before.some((v, j) => fn[edit.offset + j] !== v)) throw new Error('Patch anchor mismatch.');
              fn = bytes(fn.subarray(0, edit.offset), after, fn.subarray(edit.offset + before.length));
            }
          }
          parts.push(leb(fn.length), fn);
          at = begin + size;
        }
        for (const added of spec.additionalFunctions || []) {
          const fn = hex(added.body);
          parts.push(leb(fn.length), fn);
        }
        body = concat(parts);
      }
      output.push(section(id, body));
      p = end;
    }
    return bytes(...output);
  }
  globalThis.AzsPatch = { patch, spec };
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (location.hostname !== 'wow.aethus.pl' || window.top !== window.self) return;
  if (window.azsTrainer) return;

  const original = {
    compile: WebAssembly.compile.bind(WebAssembly),
    compileStreaming: WebAssembly.compileStreaming?.bind(WebAssembly),
    instantiate: WebAssembly.instantiate.bind(WebAssembly),
    instantiateStreaming: WebAssembly.instantiateStreaming?.bind(WebAssembly),
  };
  const state = { god: false, rapid: false, gold: false, luck: false, xp: false, area: false, bossMobs: false,
    xpMultiplier: 10, areaMultiplier: 100, interval: 0.1, ready: false, status: 'Waiting for game…',
    runActive: false, runPhase: 0, currentZone: 0, nextBoss: 0, selectedBoss: 0,
    selectedGuardian: 10, spawnZone: 0, pending: false, unlockBusy: false,
    actionMessage: 'Start a match to use run actions.' };
  const catalog = spec.catalog || [];
  let followCurrentZone = true;
  let lastAction = 0;
  let pendingCompletion;
  // Fullscreening the canvas makes outside DOM inert even when it is painted
  // above the canvas. Fullscreen the containing document so the trainer stays usable.
  for (const name of ['requestFullscreen', 'webkitRequestFullscreen']) {
    const request = Element.prototype[name];
    if (typeof request === 'function') Element.prototype[name] = function (...args) {
      return request.apply(this instanceof HTMLCanvasElement && this.id === 'benilla'
        ? document.documentElement : this, args);
    };
  }
  let exports;
  let host;
  let root;
  const apply = () => {
    if (exports) {
      exports.__azs_god.value = +state.god;
      exports.__azs_rapid.value = +state.rapid;
      exports.__azs_interval.value = state.interval;
      exports.__azs_gold.value = +state.gold;
      exports.__azs_luck.value = +state.luck;
      exports.__azs_xp.value = +state.xp;
      exports.__azs_xpMultiplier.value = state.xpMultiplier;
      exports.__azs_area.value = +state.area;
      exports.__azs_areaMultiplier.value = state.areaMultiplier;
      exports.__azs_bossMobs.value = +state.bossMobs;
      exports.__azs_replacementBoss.value = state.selectedBoss;
    }
    render();
  };
  const updateStatus = s => { state.status = s; render(); };
  const bind = result => {
    const instance = result instanceof WebAssembly.Instance ? result : result.instance;
    if (instance?.exports.__azs_god) {
      exports = instance.exports;
      state.ready = true;
      state.status = 'Ready · trainer 1.4 · game 0.120.4';
      apply();
    }
    return result;
  };
  async function compile(b) {
    const view = b instanceof ArrayBuffer ? new Uint8Array(b) :
      new Uint8Array(b.buffer, b.byteOffset, b.byteLength);
    // Other small WASM modules on the page pass through untouched.
    if (view.length < 50_000_000) return original.compile(b);
    updateStatus('Checking game build…');
    try {
      const result = await original.compile(await patch(view));
      updateStatus('Patch compiled · starting game…');
      return result;
    } catch (e) {
      state.ready = false;
      updateStatus(e.message);
      console.error('[AZS Trainer]', e);
      // An updated/unknown build continues normally, with controls disabled.
      return original.compile(b);
    }
  }
  WebAssembly.compile = compile;
  WebAssembly.compileStreaming = async response => compile(await (await response).arrayBuffer());
  WebAssembly.instantiate = async (source, imports, ...rest) => {
    if (source instanceof WebAssembly.Module) return bind(await original.instantiate(source, imports, ...rest));
    const module = await compile(source);
    const instance = await original.instantiate(module, imports, ...rest);
    bind(instance);
    return { module, instance };
  };
  WebAssembly.instantiateStreaming = async (response, imports, ...rest) =>
    WebAssembly.instantiate(await (await response).arrayBuffer(), imports, ...rest);

  function render() {
    if (!root) return;
    root.querySelector('#status').textContent = state.status;
    for (const key of ['god', 'rapid', 'gold', 'luck', 'xp', 'area', 'bossMobs']) {
      const button = root.querySelector('#' + key);
      button.textContent = ({god: '1: God mode', rapid: '2: Rapid skills', gold: '3: Unlimited gold',
        luck: '4: Legendary rolls', xp: '5: XP boost', area: '6: Skill area', bossMobs: '7: Boss enemies'}[key]) + ': ' + (state[key] ? 'ON' : 'OFF');
      button.dataset.on = String(state[key]);
      button.disabled = !state.ready;
      button.setAttribute('aria-pressed', String(state[key]));
    }
    root.querySelector('#interval').value = String(state.interval);
    root.querySelector('#xp-multiplier').value = String(state.xpMultiplier);
    root.querySelector('#area-multiplier').value = String(state.areaMultiplier);
    renderActions();
  }
  function populateChoices(zoneIndex) {
    const zone = catalog[zoneIndex];
    if (!root || !zone) return;
    state.spawnZone = zoneIndex;
    root.querySelector('#spawn-zone').value = String(zoneIndex);
    const boss = root.querySelector('#boss-choice'), guardian = root.querySelector('#guardian-choice');
    boss.replaceChildren(...zone.bosses.map(b => new Option(b.name, String(b.value))));
    guardian.replaceChildren(...zone.guardians.map(g => new Option(g.name, String(g.value))));
    state.selectedBoss = zone.bosses[Math.min(state.currentZone === zoneIndex ? state.nextBoss : 0, 4)]?.value ?? 0;
    state.selectedGuardian = zone.guardians[Math.min(10, zone.guardians.length - 1)]?.value ?? 0;
    boss.value = String(state.selectedBoss); guardian.value = String(state.selectedGuardian);
    if (exports) exports.__azs_replacementBoss.value = state.selectedBoss;
  }
  function renderActions() {
    if (!root) return;
    root.querySelector('#run-status').textContent = state.actionMessage;
    for (const name of ['spawn-boss', 'spawn-guardian', 'instant-win'])
      root.querySelector('#' + name).disabled = !state.ready || !state.runActive || state.pending || state.unlockBusy;
    root.querySelector('#unlock-all').disabled = !state.ready || !state.runActive || state.pending || state.unlockBusy;
    root.querySelector('#restore-backup').disabled = state.pending || state.unlockBusy;
    const next = root.querySelector('#spawn-next');
    next.disabled = !state.ready || !state.runActive || state.pending || state.unlockBusy || state.nextBoss >= 5;
    const boss = catalog[state.currentZone]?.bosses[state.nextBoss];
    next.textContent = boss ? 'Spawn next: ' + boss.name : 'Scheduled bosses complete';
  }
  function requestAction(command, argument = 0, internal = false) {
    if (!exports || !state.runActive || state.pending || (state.unlockBusy && !internal)) return false;
    if (!Number.isInteger(argument) || argument < 0 || argument > 0x7fffffff) return false;
    exports.__azs_actionResult.value = 0;
    exports.__azs_argument.value = argument;
    exports.__azs_command.value = command;
    lastAction = command; state.pending = true;
    state.actionMessage = command === 6 ? 'Saving a backup checkpoint…' :
      command === 5 ? 'Unlocking collection and completing the run…' :
      command === 4 ? 'Completing the run…' : 'Spawning…';
    renderActions(); return true;
  }
  function actionAndWait(command, argument = 0) {
    return new Promise((resolve, reject) => {
      if (!requestAction(command, argument, true)) {
        reject(new Error('The match is no longer ready for this action.')); return;
      }
      const timeout = setTimeout(() => {
        pendingCompletion = null;
        reject(new Error('The game did not finish the action. Keep the game tab active and try again.'));
      }, 15000);
      pendingCompletion = {resolve, reject, timeout};
    });
  }
  async function unlockAll() {
    if (!exports || !state.runActive || state.pending || state.unlockBusy) return false;
    state.unlockBusy = true; renderActions();
    try {
      if (!globalThis.AzsSaveBackup) throw new Error('Save backup support is missing. Reopen the updated trainer.');
      await AzsSaveBackup.create(() => actionAndWait(6));
      await actionAndWait(5, Math.floor(Date.now() / 1000));
      return true;
    } catch (error) {
      state.actionMessage = error.message;
      return false;
    } finally { state.unlockBusy = false; renderActions(); }
  }
  function pollRun() {
    if (!exports) return;
    try {
      const memory = exports.memory.buffer, game = exports.__azs_gamePointer.value >>> 0, run = game + 16;
      const view = new DataView(memory);
      let active = false, phase = 0;
      if (game && run + 2144 < memory.byteLength && view.getBigUint64(run, true) !== 2n) {
        phase = view.getUint8(run + 2138);
        active = (phase === 1 || phase === 2) && view.getUint32(run + 1920, true) !== 0;
        state.nextBoss = view.getUint32(run + 2020, true);
        const p = view.getUint32(run + 184, true), n = view.getUint32(run + 188, true);
        if (n <= 64 && p + n <= memory.byteLength) {
          const key = new TextDecoder().decode(new Uint8Array(memory, p, n));
          const zone = catalog.findIndex(z => z.key === key);
          if (zone >= 0 && (zone !== state.currentZone || (!state.runActive && active))) {
            state.currentZone = zone;
            if (followCurrentZone) populateChoices(zone);
          }
        }
      }
      if (!state.runActive && active && !state.pending) state.actionMessage = 'Run actions ready.';
      state.runActive = active; state.runPhase = phase;
      if (state.pending && exports.__azs_command.value === 0) {
        state.pending = false;
        const result = exports.__azs_actionResult.value;
        state.actionMessage = result === 1 ? (lastAction === 6 ? 'Save checkpoint created.' :
          lastAction === 5 ? 'Collection unlocked and victory completed. Backup retained.' :
          lastAction === 4 ? 'Victory completed.' :
          lastAction === 3 ? 'Guardian spawned. Interact to challenge it.' : 'Boss spawned near your hero.') :
          ({2:'No active match.',3:'Invalid enemy selection.',4:'That guardian is already present.',
            5:'All scheduled bosses have spawned.',6:'The world is still loading.',
            7:'Spawn did not complete.',8:'Guardians are unavailable in this run mode.'}[result] || 'Action could not complete.');
        if (pendingCompletion) {
          const completion = pendingCompletion; pendingCompletion = null;
          clearTimeout(completion.timeout);
          if (result === 1) completion.resolve();
          else completion.reject(new Error(state.actionMessage));
        }
      }
      renderActions();
    } catch (error) { console.warn('[AZS Trainer] Run status unavailable:', error); }
  }
  function mount() {
    if (!document.documentElement || host) return;
    host = document.createElement('div');
    host.id = 'azs-trainer-panel';
    host.style.cssText = 'position:fixed;inset:auto;bottom:12px;right:12px;margin:0;padding:0;border:0;background:transparent;z-index:2147483647;max-width:calc(100vw - 24px)';
    // The game fullscreens its canvas. A top-layer popover keeps the controls
    // visible AND clickable above that fullscreen element.
    if (typeof host.showPopover === 'function') host.popover = 'manual';
    root = host.attachShadow({ mode: 'open' });
    root.innerHTML = `<style>
      :host{color-scheme:dark}*{box-sizing:border-box}section{width:270px;max-height:calc(100dvh - 270px);overflow:auto;overscroll-behavior:contain;background:#121820f2;color:#eef5fc;border:1px solid #4d6174;border-radius:12px;padding:12px;font:13px/1.45 system-ui;box-shadow:0 8px 32px #0008}
      header{display:flex;justify-content:space-between;align-items:center;font-weight:650;position:sticky;top:-12px;background:#121820;padding:4px 0;z-index:1}header button{width:auto;padding:1px 8px;margin:0}
      #status{font-size:11px;color:#aec1d2;margin:7px 0;overflow-wrap:anywhere}button,select{font:inherit;color:inherit;border:1px solid #53677a;border-radius:6px;background:#25313e;padding:7px;cursor:pointer}button{width:100%;margin:4px 0;text-align:left}button[data-on=true]{background:#185d45;border-color:#49bf8d}button:disabled{opacity:.5;cursor:default}label{display:block;margin-top:6px}select{width:100%;margin-top:4px}small{display:block;font-size:11px;color:#afbfcc;margin-top:8px}[hidden]{display:none!important}
      details{border:1px solid #53677a;border-radius:6px;padding:7px;margin:7px 0}summary{cursor:pointer;font-weight:600}#run-status{font-size:11px;color:#b8cbd9;margin:5px 0}#instant-win{border-color:#b59145;background:#4c391b}
      </style><section aria-label="Azeroth Survivors trainer"><header>AZS Trainer 1.4 <button id="collapse" aria-label="Collapse trainer">−</button></header>
      <div id="body"><div id="status" role="status"></div>
      <details id="spawner"><summary>Boss & guardian spawner</summary>
      <label>Enemy source zone<select id="spawn-zone"></select></label>
      <label>Boss / boss-enemy replacement<select id="boss-choice"></select></label><button id="spawn-boss">Spawn selected boss</button><button id="spawn-next">Spawn next scheduled boss</button>
      <label>Guardian / rare enemy<select id="guardian-choice"></select></label><button id="spawn-guardian">Spawn selected guardian</button>
      <small>Manual spawns keep the normal schedule. The next-boss button advances it. A final boss can end the run when defeated.</small></details>
      <button id="instant-win">Instant win</button><div id="run-status" role="status"></div>
      <details><summary>Permanent collection unlocks</summary>
      <button id="unlock-all">Unlock collection & win</button>
      <small>Permanently unlocks collection progress for every class. A verified save backup is created first.</small>
      <button id="restore-backup">Download last pre-unlock backup</button></details>
      <button id="god" aria-pressed="false"></button><button id="rapid" aria-pressed="false"></button><button id="gold" aria-pressed="false"></button><button id="luck" aria-pressed="false"></button><button id="xp" aria-pressed="false"></button><button id="area" aria-pressed="false"></button><button id="bossMobs" aria-pressed="false"></button>
      <label>Skill cooldown<select id="interval"><option value="0.25">0.25 seconds</option><option value="0.1">0.10 seconds</option><option value="0">0 · every frame</option></select></label>
      <label>XP multiplier<select id="xp-multiplier"><option value="2">2×</option><option value="5">5×</option><option value="10">10×</option><option value="100">100×</option></select></label>
      <label>Area multiplier<select id="area-multiplier"><option value="2">2×</option><option value="5">5×</option><option value="10">10×</option><option value="25">25×</option><option value="100">100× · maximum preset</option></select></label>
      <small>1–7: toggle cheats · numpad works too.<br>Boss enemies uses the selected boss for NEW normal spawns.<br>Click level-up cards to choose them.</small></div></section>`;
    for (const key of ['god', 'rapid', 'gold', 'luck', 'xp', 'area', 'bossMobs']) root.querySelector('#' + key).onclick = () => { state[key] = !state[key]; apply(); };
    root.querySelector('#spawn-zone').replaceChildren(...catalog.map(z => new Option(z.name, String(z.index))));
    populateChoices(0);
    root.querySelector('#spawn-zone').onchange = e => { followCurrentZone = false; populateChoices(Number(e.target.value)); };
    root.querySelector('#boss-choice').onchange = e => { state.selectedBoss = Number(e.target.value); apply(); };
    root.querySelector('#guardian-choice').onchange = e => { state.selectedGuardian = Number(e.target.value); };
    root.querySelector('#spawn-boss').onclick = () => requestAction(2, state.selectedBoss);
    root.querySelector('#spawn-next').onclick = () => requestAction(1);
    root.querySelector('#spawn-guardian').onclick = () => requestAction(3, state.selectedGuardian);
    root.querySelector('#instant-win').onclick = () => requestAction(4);
    root.querySelector('#unlock-all').onclick = () => { void unlockAll(); };
    root.querySelector('#restore-backup').onclick = async () => {
      try {
        await AzsSaveBackup.downloadLatest(); state.actionMessage = 'Backup downloaded. Restore through Options > Saves > Import Save.';
      } catch (error) { state.actionMessage = error.message; }
      renderActions();
    };
    root.querySelector('#interval').onchange = e => { state.interval = Number(e.target.value); apply(); };
    root.querySelector('#xp-multiplier').onchange = e => { state.xpMultiplier = Number(e.target.value); apply(); };
    root.querySelector('#area-multiplier').onchange = e => { state.areaMultiplier = Number(e.target.value); apply(); };
    root.querySelector('#collapse').onclick = e => {
      const body = root.querySelector('#body'); body.hidden = !body.hidden;
      e.target.textContent = body.hidden ? '+' : '−';
    };
    document.documentElement.append(host);
    const raise = () => {
      if (host.popover === 'manual') {
        if (host.matches(':popover-open')) host.hidePopover();
        host.showPopover();
      }
    };
    raise();
    document.addEventListener('fullscreenchange', raise);
    document.addEventListener('webkitfullscreenchange', raise);
    render();
  }
  window.azsTrainer = {
    get state() { return { ...state }; },
    set(settings) {
      if (typeof settings.god === 'boolean') state.god = settings.god;
      if (typeof settings.rapid === 'boolean') state.rapid = settings.rapid;
      if (typeof settings.gold === 'boolean') state.gold = settings.gold;
      if (typeof settings.luck === 'boolean') state.luck = settings.luck;
      if (typeof settings.xp === 'boolean') state.xp = settings.xp;
      if (typeof settings.area === 'boolean') state.area = settings.area;
      if (typeof settings.bossMobs === 'boolean') state.bossMobs = settings.bossMobs;
      if (Number.isInteger(settings.selectedBoss) && settings.selectedBoss >= 0 && settings.selectedBoss < 60) {
        followCurrentZone = false; populateChoices(Math.floor(settings.selectedBoss / 5)); state.selectedBoss = settings.selectedBoss;
        if (root) root.querySelector('#boss-choice').value = String(settings.selectedBoss);
      }
      if ([2, 5, 10, 100].includes(settings.xpMultiplier)) state.xpMultiplier = settings.xpMultiplier;
      if ([2, 5, 10, 25, 100].includes(settings.areaMultiplier)) state.areaMultiplier = settings.areaMultiplier;
      if ([0, 0.1, 0.25].includes(settings.interval)) state.interval = settings.interval;
      apply();
    },
    spawnBoss(value = state.selectedBoss) { return requestAction(2, value); },
    spawnNextBoss() { return requestAction(1); },
    spawnGuardian(value = state.selectedGuardian) { return requestAction(3, value); },
    win() { return requestAction(4); },
    unlockAll,
    disable() { state.god = state.rapid = state.gold = state.luck = state.xp = state.area = state.bossMobs = false; apply(); },
  };
  const heldHotkeys = new Set();
  window.addEventListener('keydown', event => {
    if (!state.ready || event.ctrlKey || event.altKey || event.metaKey ||
        /INPUT|TEXTAREA|SELECT/.test(event.target?.tagName || '') ||
        event.composedPath().some(n => n === host)) return;
    const key = {Digit1: 'god', Digit2: 'rapid', Digit3: 'gold', Digit4: 'luck', Digit5: 'xp', Digit6: 'area', Digit7: 'bossMobs',
      Numpad1: 'god', Numpad2: 'rapid', Numpad3: 'gold', Numpad4: 'luck', Numpad5: 'xp', Numpad6: 'area', Numpad7: 'bossMobs'}[event.code];
    if (key) {
      heldHotkeys.add(event.code);
      event.preventDefault(); event.stopImmediatePropagation();
      if (!event.repeat) { state[key] = !state[key]; apply(); }
    }
  }, true);
  window.addEventListener('keyup', event => {
    if (heldHotkeys.delete(event.code)) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);
  window.addEventListener('blur', () => heldHotkeys.clear());
  setInterval(pollRun, 250);
  mount();
  if (!host) new MutationObserver((_, observer) => { mount(); if (host) observer.disconnect(); })
    .observe(document, { childList: true, subtree: true });
})();
