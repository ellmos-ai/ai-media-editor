// Gemeinsame Helfer der Halloween-Szenen (HyperFrames). Deterministisch: kein Date/performance.now, kein Math.random.
(function (root) {
  const HFX = (function () {
    const NS = "http://www.w3.org/2000/svg";

    // mulberry32 — gesäter Zufall
    function rng(seed) {
      let a = seed >>> 0;
      return function () {
        a = (a + 0x6d2b79f5) >>> 0;
        let t = a;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    }

    // glattes 1D-Rauschen 0..1
    function noise1(seed) {
      const r = rng(seed);
      const v = Array.from({ length: 1024 }, r);
      return function (x) {
        const i = Math.floor(x), f = x - i, s = f * f * (3 - 2 * f);
        return v[i & 1023] * (1 - s) + v[(i + 1) & 1023] * s;
      };
    }

    function el(tag, attrs, parent) {
      const e = document.createElementNS(NS, tag);
      for (const k in attrs) e.setAttribute(k, attrs[k]);
      if (parent) parent.appendChild(e);
      return e;
    }

    // Zeitgetriebene Szene: fn(t) wird für jede gesuchte Zeit aufgerufen (seek-sicher).
    function drive(tl, dur, fn) {
      const p = { t: 0 };
      fn(0);
      tl.to(p, { t: dur, duration: dur, ease: "none", onUpdate: () => fn(p.t) }, 0);
    }

    const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
    const lerp = (a, b, k) => a + (b - a) * k;
    const smooth = (e0, e1, x) => { const k = clamp((x - e0) / (e1 - e0), 0, 1); return k * k * (3 - 2 * k); };

    // Keyframes [[t, v], ...] mit weicher Interpolation zwischen den Stützstellen
    function key(t, ks) {
      if (t <= ks[0][0]) return ks[0][1];
      for (let i = 1; i < ks.length; i++) if (t <= ks[i][0]) return lerp(ks[i - 1][1], ks[i][1], smooth(ks[i - 1][0], ks[i][0], t));
      return ks[ks.length - 1][1];
    }
    // Glocke 0→1→0 zwischen a und b
    const bump = (t, a, b) => (t <= a || t >= b ? 0 : Math.sin((Math.PI * (t - a)) / (b - a)));

    // fromTo ohne Sofort-Render: Startzustand erst ab Tween-Beginn sichtbar
    const ft = (tl, target, from, to, pos) => tl.fromTo(target, from, Object.assign({ immediateRender: false }, to), pos);

    // Stückweise Bahn: pts = [[t, x, y], ...] → {x, y, dir, moving, dist}
    function path(pts) {
      const cum = [0];
      for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][1] - pts[i - 1][1], pts[i][2] - pts[i - 1][2]));
      let lastDir = Math.atan2(pts[1][2] - pts[0][2], pts[1][1] - pts[0][1]);
      const dirs = pts.map((p, i) => {
        if (i === pts.length - 1) return null;
        const dx = pts[i + 1][1] - p[1], dy = pts[i + 1][2] - p[2];
        if (Math.hypot(dx, dy) > 0.5) lastDir = Math.atan2(dy, dx);
        return lastDir;
      });
      return function (t) {
        if (t <= pts[0][0]) return { x: pts[0][1], y: pts[0][2], dir: dirs[0], moving: false, dist: 0 };
        for (let i = 0; i < pts.length - 1; i++) {
          const a = pts[i], b = pts[i + 1];
          if (t <= b[0]) {
            const k = (t - a[0]) / Math.max(1e-6, b[0] - a[0]);
            const seg = Math.hypot(b[1] - a[1], b[2] - a[2]);
            return { x: lerp(a[1], b[1], k), y: lerp(a[2], b[2], k), dir: dirs[i], moving: seg > 0.5, dist: cum[i] + seg * k };
          }
        }
        const z = pts[pts.length - 1];
        return { x: z[1], y: z[2], dir: dirs[pts.length - 2], moving: false, dist: cum[cum.length - 1] };
      };
    }

    // Spinne in Draufsicht, Kopf zeigt nach +x. Beine als verschachtelte Gelenkgruppen (Vorwärtskinematik).
    // opt: {size, seed, detail}; liefert {g, pose(phase, twitch)}
    function spider(parent, opt) {
      const s = opt.size, detail = !!opt.detail;
      const g = el("g", {}, parent);
      const legsG = el("g", {}, g);
      const body = el("g", {}, g);
      const base = [-58, -22, 18, 52];        // Grundwinkel rechte Seite (Grad, 0 = +y-Achse bei Kopf +x)
      const knee = [-38, -14, 16, 34];
      const L = [0.62, 0.66, 0.58, 0.7].map((k) => k * s);
      const legs = [];
      const stroke = detail ? "#7a6656" : "#6e5c4e";
      for (let side = -1; side <= 1; side += 2) {
        for (let i = 0; i < 4; i++) {
          const ax = s * (0.12 - i * 0.07), ay = side * s * 0.07;
          const rootG = el("g", { transform: `translate(${ax},${ay})` }, legsG);
          const fem = el("g", {}, rootG);
          const lf = L[i] * 0.45, lt = L[i] * 0.4, lr = L[i] * 0.3;
          segment(fem, lf, s * 0.05, stroke, detail);
          const tib = el("g", {}, fem);
          segment(tib, lt, s * 0.04, stroke, detail);
          const tar = el("g", {}, tib);
          segment(tar, lr, s * 0.028, stroke, detail);
          legs.push({ side, i, fem, tib, tar, lf, lt, group: (i + (side > 0 ? 0 : 1)) % 2 });
        }
      }
      // Körper: Hinterleib, Kopfbrust, Augen
      const id = "sp" + (opt.seed || 1);
      const defs = el("defs", {}, g);
      const grad = el("radialGradient", { id: id + "a", cx: "40%", cy: "35%", r: "70%" }, defs);
      el("stop", { offset: "0%", "stop-color": "#b49a80" }, grad);
      el("stop", { offset: "55%", "stop-color": "#5c4a3c" }, grad);
      el("stop", { offset: "100%", "stop-color": "#2a201a" }, grad);
      el("ellipse", { cx: -s * 0.3, cy: 0, rx: s * 0.3, ry: s * 0.22, fill: `url(#${id}a)` }, body);
      if (detail) {
        for (let k = 0; k < 4; k++) el("path", { d: `M${-s * (0.12 + k * 0.1)},${-s * 0.06} L${-s * (0.17 + k * 0.1)},0 L${-s * (0.12 + k * 0.1)},${s * 0.06}`, fill: "none", stroke: "#c9b39a", "stroke-width": s * 0.012, opacity: 0.55 }, body);
      }
      el("ellipse", { cx: s * 0.08, cy: 0, rx: s * 0.15, ry: s * 0.12, fill: `url(#${id}a)` }, body);
      el("ellipse", { cx: s * 0.22, cy: 0, rx: s * 0.06, ry: s * 0.065, fill: "#4a3a30" }, body);
      for (let k = -1; k <= 1; k += 2) {
        el("circle", { cx: s * 0.255, cy: k * s * 0.025, r: s * 0.014, fill: "#e8d8c8" }, body);
        if (detail) el("circle", { cx: s * 0.235, cy: k * s * 0.045, r: s * 0.009, fill: "#d8c0b0" }, body);
        el("path", { d: `M${s * 0.27},${k * s * 0.02} q${s * 0.05},${k * s * 0.005} ${s * 0.06},${k * s * 0.03}`, stroke: "#3a2c24", "stroke-width": s * 0.022, fill: "none", "stroke-linecap": "round" }, body);
      }
      const twitchN = noise1((opt.seed || 1) * 7 + 3);
      function pose(phase, twitch, t) {
        for (const lg of legs) {
          const ph = phase + (lg.group ? Math.PI : 0) + lg.i * 0.35;
          const sweep = 16 * Math.sin(ph);
          const tw = twitch ? (twitchN(t * 3 + lg.i * 11 + (lg.side + 1) * 37) - 0.5) * twitch : 0;
          const a = lg.side * (90 + base[lg.i] + sweep + tw);
          const kb = lg.side * (knee[lg.i] + 6 * Math.cos(ph) + tw * 0.5);
          lg.fem.setAttribute("transform", `rotate(${a})`);
          lg.tib.setAttribute("transform", `translate(${lg.lf},0) rotate(${kb})`);
          lg.tar.setAttribute("transform", `translate(${lg.lt},0) rotate(${kb * 0.6})`);
        }
      }
      pose(0, 0, 0);
      return { g, pose };
    }

    function segment(parent, len, w, color, detail) {
      el("line", { x1: 0, y1: 0, x2: len, y2: 0, stroke: "#241a14", "stroke-width": w * 1.35, "stroke-linecap": "round" }, parent);
      el("line", { x1: 0, y1: 0, x2: len, y2: 0, stroke: color, "stroke-width": w, "stroke-linecap": "round" }, parent);
      if (detail) {
        for (let k = 1; k < 7; k++) {
          const x = (len * k) / 7;
          el("line", { x1: x, y1: -w * 0.5, x2: x + w * 0.45, y2: -w * 0.95, stroke: color, "stroke-width": w * 0.14, opacity: 0.55 }, parent);
          el("line", { x1: x, y1: w * 0.5, x2: x + w * 0.45, y2: w * 0.95, stroke: color, "stroke-width": w * 0.14, opacity: 0.55 }, parent);
        }
      }
    }

    // Fledermaus frontal; flap(k) mit k 0..1 (0 = Flügel oben)
    function bat(parent, size) {
      const s = size;
      const g = el("g", {}, parent);
      const mk = (side) => {
        const w = el("g", {}, g);
        el("path", {
          d: `M0,0 C${side * s * 0.25},${-s * 0.35} ${side * s * 0.7},${-s * 0.4} ${side * s},${-s * 0.15} C${side * s * 0.85},${-s * 0.05} ${side * s * 0.8},${s * 0.1} ${side * s * 0.72},${s * 0.12} C${side * s * 0.6},${s * 0.02} ${side * s * 0.5},${s * 0.05} ${side * s * 0.45},${s * 0.18} C${side * s * 0.35},${s * 0.08} ${side * s * 0.25},${s * 0.1} ${side * s * 0.15},${s * 0.2} Z`,
          fill: "#3c2f4a", stroke: "#7d6a96", "stroke-width": s * 0.01,
        }, w);
        for (const [bx, by] of [[1, -0.15], [0.72, 0.12], [0.45, 0.18], [0.15, 0.2]]) el("path", { d: `M0,0 L${side * s * bx * 0.92},${s * by * 0.9}`, stroke: "#6d5a84", "stroke-width": s * 0.012, fill: "none" }, w);
        return w;
      };
      const wl = mk(-1), wr = mk(1);
      el("ellipse", { cx: 0, cy: s * 0.05, rx: s * 0.09, ry: s * 0.17, fill: "#3e3048", stroke: "#8f7aa8", "stroke-width": s * 0.01 }, g);
      el("circle", { cx: 0, cy: -s * 0.12, r: s * 0.08, fill: "#3e3048", stroke: "#8f7aa8", "stroke-width": s * 0.01 }, g);
      for (const k of [-1, 1]) {
        el("path", { d: `M${k * s * 0.03},${-s * 0.17} L${k * s * 0.07},${-s * 0.29} L${k * s * 0.08},${-s * 0.15} Z`, fill: "#3e3048", stroke: "#8f7aa8", "stroke-width": s * 0.008 }, g);
        el("circle", { cx: k * s * 0.032, cy: -s * 0.125, r: s * 0.016, fill: "#ff3a2a" }, g);
      }
      function flap(k) {
        const a = 35 - 70 * k, sy = 1 - 0.55 * Math.sin(k * Math.PI) * 0.6;
        wl.setAttribute("transform", `rotate(${-a}) scale(1,${sy})`);
        wr.setAttribute("transform", `rotate(${a}) scale(1,${sy})`);
      }
      flap(0.5);
      return { g, flap };
    }

    return { NS, rng, noise1, el, drive, clamp, lerp, smooth, key, bump, ft, path, spider, bat };
  })();

  if (root) root.HFX = HFX;
  if (typeof window !== "undefined") window.HFX = HFX;
  if (typeof module !== "undefined" && module.exports) module.exports = HFX;
})(typeof globalThis !== "undefined" ? globalThis : typeof window !== "undefined" ? window : this);
