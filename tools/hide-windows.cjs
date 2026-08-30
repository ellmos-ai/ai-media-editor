// hide-windows.cjs — Node-Preload gegen Konsolenfenster-Bursts unter Windows.
//
// Problem: Node-Werkzeuge (HyperFrames, Playwright-Aufrufe, ffmpeg-Spawns) starten pro Schritt viele
// kurze Kindprozesse. Ein Konsolenprogramm bekommt dabei ein NEUES sichtbares Konsolenfenster, wenn
// der Spawn ohne `windowsHide` laeuft. Dieses Preload umhuellt child_process und erzwingt
// `windowsHide: true` fuer jeden Spawn — ohne das Werkzeug selbst zu patchen.
//
// Nutzung (Windows):  set NODE_OPTIONS=--require "C:\pfad\tools\hide-windows.cjs"
//                     npx hyperframes render ...
// Bequem: tools\hf.cmd (setzt NODE_OPTIONS und ruft npx hyperframes auf).
// Auf anderen Plattformen ist das Preload ein No-op. Ticket: T-20260829-486029203.
'use strict';
if (process.platform === 'win32' && !process.env.HIDE_WINDOWS_PRELOAD_OFF) {
  const cp = require('child_process');
  const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v) && !Buffer.isBuffer(v);
  const wrap = (name) => {
    const orig = cp[name];
    if (typeof orig !== 'function') return;
    const wrapped = function (...args) {
      let cb = null;
      if (typeof args[args.length - 1] === 'function') cb = args.pop();
      const last = args.length - 1;
      if (last >= 1 && isPlainObject(args[last])) {
        // erzwingen — auch gegen ein explizites windowsHide:false des Aufrufers (Escape: HIDE_WINDOWS_PRELOAD_OFF=1)
        args[last] = Object.assign({}, args[last], { windowsHide: true });
      } else {
        args.push({ windowsHide: true });
      }
      if (cb) args.push(cb);
      return orig.apply(this, args);
    };
    Object.defineProperty(wrapped, 'name', { value: name });
    cp[name] = wrapped;
  };
  ['spawn', 'spawnSync', 'exec', 'execSync', 'execFile', 'execFileSync', 'fork'].forEach(wrap);
  if (process.env.HIDE_WINDOWS_DEBUG) process.stderr.write(`[hide-windows] aktiv in pid ${process.pid} (${process.argv.slice(1, 2).join(' ')})\n`);
}
