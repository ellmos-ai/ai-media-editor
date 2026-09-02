// hide-windows.cjs — Node-Preload gegen Konsolenfenster-Bursts unter Windows.
//
// Problem: Node-Werkzeuge (HyperFrames/Puppeteer, Playwright-Aufrufe, ffmpeg-Spawns) starten pro Schritt viele
// kurze Kindprozesse. Ein Konsolenprogramm bekommt dabei ein NEUES sichtbares Konsolenfenster, wenn
// der Spawn ohne `windowsHide` laeuft. Dieses Preload umhuellt child_process und erzwingt
// `windowsHide: true` fuer jeden Spawn — ohne das Werkzeug selbst zu patchen.
// Fuer HyperFrames bevorzugt tools/hf.cmd zusaetzlich ein installiertes regulaeres Chrome: dessen
// Windows-GUI-Subsystem erzeugte im Gegensatz zu chrome-headless-shell kein PseudoConsoleWindow.
//
// Nutzung (Windows):  set NODE_OPTIONS=--require "C:\pfad\tools\hide-windows.cjs"
//                     npx hyperframes render ...
// Bequem: tools\hf.cmd (setzt NODE_OPTIONS und ruft npx hyperframes auf).
// Auf anderen Plattformen ist das Preload ein No-op. Ticket: T-20260829-486029203.
'use strict';

const fs = require('fs');
const path = require('path');

function systemChromeCandidates(env = process.env) {
  const candidates = [];
  const add = (root) => {
    if (typeof root !== 'string' || !root.trim()) return;
    candidates.push(path.join(root, 'Google', 'Chrome', 'Application', 'chrome.exe'));
  };

  add(env.ProgramW6432);
  add(env.PROGRAMFILES);
  add(env['ProgramFiles(x86)']);
  add(env.LOCALAPPDATA);

  const seen = new Set();
  return candidates.filter((candidate) => {
    const key = candidate.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function findSystemChrome(env = process.env, exists = fs.existsSync) {
  return systemChromeCandidates(env).find((candidate) => exists(candidate));
}

function configureHyperframesBrowser(env = process.env, exists = fs.existsSync) {
  if (env.HYPERFRAMES_BROWSER_PATH) {
    return { executablePath: env.HYPERFRAMES_BROWSER_PATH, source: 'explicit' };
  }
  if (env.HF_PREFER_FULL_CHROME !== '1') return undefined;

  const executablePath = findSystemChrome(env, exists);
  if (!executablePath) return undefined;
  env.HYPERFRAMES_BROWSER_PATH = executablePath;
  return { executablePath, source: 'system-full-chrome' };
}

if (process.platform === 'win32' && !process.env.HIDE_WINDOWS_PRELOAD_OFF) {
  const cp = require('child_process');
  const browser = configureHyperframesBrowser();
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
  if (process.env.HIDE_WINDOWS_DEBUG) {
    process.stderr.write(`[hide-windows] aktiv in pid ${process.pid} (${process.argv.slice(1, 2).join(' ')})\n`);
    if (browser?.source === 'system-full-chrome') {
      process.stderr.write(`[hide-windows] HyperFrames nutzt regulaeres Chrome: ${browser.executablePath}\n`);
    }
  }
}

module.exports = { configureHyperframesBrowser, findSystemChrome, systemChromeCandidates };
