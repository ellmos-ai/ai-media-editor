'use strict';

const assert = require('assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

process.env.HIDE_WINDOWS_PRELOAD_OFF = '1';
const {
  configureHyperframesBrowser,
  findSystemChrome,
  systemChromeCandidates,
} = require('../tools/hide-windows.cjs');
delete process.env.HIDE_WINDOWS_PRELOAD_OFF;

const fakeEnv = {
  PROGRAMFILES: 'C:\\Program Files',
  'ProgramFiles(x86)': 'C:\\Program Files (x86)',
  LOCALAPPDATA: 'C:\\Users\\Example\\AppData\\Local',
};
const expected = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

assert.deepEqual(systemChromeCandidates(fakeEnv), [
  expected,
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Users\\Example\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe',
]);
assert.equal(findSystemChrome(fakeEnv, (candidate) => candidate === expected), expected);

const selectedEnv = { ...fakeEnv, HF_PREFER_FULL_CHROME: '1' };
assert.deepEqual(configureHyperframesBrowser(selectedEnv, (candidate) => candidate === expected), {
  executablePath: expected,
  source: 'system-full-chrome',
});
assert.equal(selectedEnv.HYPERFRAMES_BROWSER_PATH, expected);

const explicitEnv = {
  ...fakeEnv,
  HF_PREFER_FULL_CHROME: '1',
  HYPERFRAMES_BROWSER_PATH: 'D:\\Portable\\Chrome\\chrome.exe',
};
assert.deepEqual(configureHyperframesBrowser(explicitEnv, () => {
  throw new Error('explicit override must not trigger discovery');
}), {
  executablePath: 'D:\\Portable\\Chrome\\chrome.exe',
  source: 'explicit',
});

const disabledEnv = { ...fakeEnv, HF_PREFER_FULL_CHROME: '0' };
assert.equal(configureHyperframesBrowser(disabledEnv, () => true), undefined);
assert.equal(disabledEnv.HYPERFRAMES_BROWSER_PATH, undefined);

function runWrapper(extraEnv = {}) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hf-wrapper-test-'));
  const probe = path.join(temp, 'probe.cjs');
  const npx = path.join(temp, 'npx.cmd');
  const runner = path.join(temp, 'run-wrapper.cmd');
  fs.writeFileSync(probe, "console.log(JSON.stringify({ browser: process.env.HYPERFRAMES_BROWSER_PATH || null, prefer: process.env.HF_PREFER_FULL_CHROME || null }));\n");
  fs.writeFileSync(npx, '@echo off\r\nnode "%~dp0probe.cjs"\r\n');

  const env = { ...process.env, ...extraEnv, PATH: `${temp};${process.env.PATH}` };
  for (const [key, value] of Object.entries(extraEnv)) {
    if (value === null) delete env[key];
  }
  try {
    const wrapper = path.resolve(__dirname, '..', 'tools', 'hf.cmd');
    fs.writeFileSync(runner, `@echo off\r\ncall "${wrapper}" --version\r\n`);
    const result = spawnSync('cmd.exe', ['/d', '/c', runner], {
      encoding: 'utf8',
      env,
      windowsHide: true,
    });
    assert.equal(result.status, 0, result.stderr || result.stdout);
    return JSON.parse(result.stdout.trim().split(/\r?\n/).at(-1));
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
}

const installedChrome = findSystemChrome(process.env);
const automatic = runWrapper({
  HYPERFRAMES_BROWSER_PATH: null,
  HF_PREFER_FULL_CHROME: null,
  HIDE_WINDOWS_PRELOAD_OFF: null,
});
assert.equal(automatic.prefer, '1');
assert.equal(automatic.browser, installedChrome || null);

const optedOut = runWrapper({
  HYPERFRAMES_BROWSER_PATH: null,
  HF_PREFER_FULL_CHROME: '0',
  HIDE_WINDOWS_PRELOAD_OFF: null,
});
assert.equal(optedOut.prefer, '0');
assert.equal(optedOut.browser, null);

const explicit = runWrapper({
  HYPERFRAMES_BROWSER_PATH: 'D:\\Portable\\Chrome\\chrome.exe',
  HF_PREFER_FULL_CHROME: null,
  HIDE_WINDOWS_PRELOAD_OFF: null,
});
assert.equal(explicit.browser, 'D:\\Portable\\Chrome\\chrome.exe');

console.log('test_hide_windows: ok');
