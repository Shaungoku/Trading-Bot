/**
 * WalformSurfaces.jsx — Interactive Website
 *
 * IMAGES: Place in an "images/" folder next to this file:
 *   images/logo.png         — Walform logo (white version)
 *   images/veneer-01.jpg    — Dark chocolate brown silk
 *   images/veneer-02.jpg    — Tobacco brown silk
 *   images/veneer-03.jpg    — Sand/beige silk
 *   images/veneer-04.jpg    — Mocha silk
 *   images/veneer-05.jpg    — Linen silk
 *   images/veneer-06.jpg    — Teak natural
 *   images/veneer-07.jpg    — Driftwood
 *   images/veneer-08.jpg    — Fog oak
 *   images/veneer-09.jpg    — Storm grain
 *   images/veneer-10.jpg    — Espresso
 *   images/veneer-11.jpg    — Dark walnut
 *   images/veneer-12.jpg    — Truffle
 *   images/veneer-13.jpg    — Honey grain
 *   images/veneer-14.jpg    — Bamboo reed (ribbed)
 *
 * DEPENDENCIES: React 18+ only — no additional packages required.
 */

import { useState, useEffect, useRef } from "react";

// ════════════════════════════════════════════════════════════════
//  FORM SERVICE — Formspree
//  Steps:
//    1. Go to https://formspree.io → Sign up free
//    2. Click "New Form" → set email to: sales@walformsurfaces.com
//    3. Copy the 8-character Form ID (e.g. "xpzgvdqr")
//    4. Paste it below replacing YOUR_FORM_ID
// ════════════════════════════════════════════════════════════════
const FORMSPREE_ID = "mwvrvaql";   // ← paste your ID here

// ════════════════════════════════════════════════════════════════
//  DESIGN TOKENS
// ════════════════════════════════════════════════════════════════

const C = {
  bg: "#0C0908",           // near-black with warm ebony undertone
  bgAlt: "#131109",        // dark walnut surface
  cream: "#F2EDE4",        // warm birch white
  brown: "#8B6040",        // primary walnut brown
  brownLight: "#B08060",   // lighter teak
  muted: "#7A6858",        // mid warm taupe
  border: "rgba(139,96,64,0.22)", // subtle wood-brown border
};

const T = {
  label: { fontSize: 11, letterSpacing: "0.2em", textTransform: "uppercase", color: C.brown, fontFamily: "sans-serif", margin: 0 },
  h1: { fontSize: "clamp(52px,7vw,100px)", fontWeight: 300, lineHeight: 1.03, letterSpacing: "-0.025em", color: C.cream, fontFamily: "Georgia,serif", margin: 0 },
  h2: { fontSize: "clamp(30px,4vw,54px)", fontWeight: 300, lineHeight: 1.1, letterSpacing: "-0.01em", color: C.cream, fontFamily: "Georgia,serif", margin: 0 },
  body: { fontSize: 16, lineHeight: 1.8, color: C.muted, fontFamily: "sans-serif", margin: 0 },
};

// ════════════════════════════════════════════════════════════════
//  DATA
// ════════════════════════════════════════════════════════════════

const VENEERS = [
  { id: 1,  name: "Ebony Strand",  finish: "Silk",   tone: "Dark",   file: "veneer-01.jpg", bg: "#2A1F1A" },
  { id: 2,  name: "Tobacco Silk",  finish: "Silk",   tone: "Dark",   file: "veneer-02.jpg", bg: "#3B2A1E" },
  { id: 3,  name: "Sand Drift",    finish: "Silk",   tone: "Light",  file: "veneer-03.jpg", bg: "#BCA898" },
  { id: 4,  name: "Mocha Grain",   finish: "Silk",   tone: "Medium", file: "veneer-04.jpg", bg: "#7A5E4A" },
  { id: 5,  name: "Linen Oak",     finish: "Silk",   tone: "Light",  file: "veneer-05.jpg", bg: "#C4B09A" },
  { id: 6,  name: "Teak Natural",  finish: "Raw",    tone: "Medium", file: "veneer-06.jpg", bg: "#8B6E55" },
  { id: 7,  name: "Driftwood",     finish: "Raw",    tone: "Medium", file: "veneer-07.jpg", bg: "#9C8878" },
  { id: 8,  name: "Fog Oak",       finish: "Raw",    tone: "Medium", file: "veneer-08.jpg", bg: "#6E6058" },
  { id: 9,  name: "Storm Grain",   finish: "Raw",    tone: "Dark",   file: "veneer-09.jpg", bg: "#5A5550" },
  { id: 10, name: "Espresso",      finish: "Raw",    tone: "Dark",   file: "veneer-10.jpg", bg: "#2E2420" },
  { id: 11, name: "Dark Walnut",   finish: "Raw",    tone: "Dark",   file: "veneer-11.jpg", bg: "#3A2C22" },
  { id: 12, name: "Truffle",       finish: "Raw",    tone: "Dark",   file: "veneer-12.jpg", bg: "#4A3828" },
  { id: 13, name: "Honey Grain",   finish: "Raw",    tone: "Medium", file: "veneer-13.jpg", bg: "#8A7060" },
  { id: 14, name: "Bamboo Reed",   finish: "Ribbed", tone: "Medium", file: "veneer-14.jpg", bg: "#6A5040" },
];

const FOUNDERS = [
  { name: "Shaun Wadhwana", role: "Co-Founder" },
  { name: "Manan Chhedda",  role: "Co-Founder" },
  { name: "Krish Wadhwana", role: "Co-Founder" },
];

// ════════════════════════════════════════════════════════════════
//  WEBGL SMOKE BACKGROUND
// ════════════════════════════════════════════════════════════════

const FRAG_SHADER = `#version 300 es
precision highp float;
out vec4 O;
uniform float time;
uniform vec2 resolution;
uniform vec3 u_color;
#define FC gl_FragCoord.xy
#define R resolution
#define T (time+660.)
float rnd(vec2 p){p=fract(p*vec2(12.9898,78.233));p+=dot(p,p+34.56);return fract(p.x*p.y);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p),u=f*f*(3.-2.*f);return mix(mix(rnd(i),rnd(i+vec2(1,0)),u.x),mix(rnd(i+vec2(0,1)),rnd(i+1.),u.x),u.y);}
float fbm(vec2 p){float t=.0,a=1.;for(int i=0;i<5;i++){t+=a*noise(p);p*=mat2(1,-1.2,.2,1.2)*2.;a*=.5;}return t;}
void main(){
  vec2 uv=(FC-.5*R)/R.y;
  // Neutral warm-brown base — balanced channels to avoid red/orange cast
  vec3 col=vec3(0.72, 0.60, 0.48);
  uv.x+=.25;
  uv*=vec2(2,1);
  float n=fbm(uv*.28-vec2(T*.01,0));
  n=noise(uv*3.+n*2.);
  // Even subtraction across channels keeps the neutral brown tone
  col.r-=fbm(uv+vec2(0,T*.015)+n) * 0.62;
  col.g-=fbm(uv*1.003+vec2(0,T*.015)+n+.003) * 0.68;
  col.b-=fbm(uv*1.006+vec2(0,T*.015)+n+.006) * 0.80;
  col=mix(col,u_color,dot(col,vec3(.28,.54,.18)));
  col=mix(vec3(.05,0.04,0.03),col,min(time*.1,1.));
  col=clamp(col,.0,1.);
  O=vec4(col,1);
}`;

const VERT_SHADER = `#version 300 es
precision highp float;
in vec4 position;
void main(){gl_Position=position;}`;

function hexToRgb(hex) {
  const r = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return r ? [parseInt(r[1], 16) / 255, parseInt(r[2], 16) / 255, parseInt(r[3], 16) / 255] : null;
}

class WGLRenderer {
  constructor(canvas, fragSrc) {
    this.canvas = canvas;
    this.gl = canvas.getContext("webgl2");
    this.color = hexToRgb("#7A4E28") || [0.478, 0.306, 0.157];
    this.animId = null;
    if (!this.gl) { console.warn("WebGL2 not available"); return; }
    this._setup(fragSrc);
    this._init();
  }

  _compile(shader, src) {
    const gl = this.gl;
    gl.shaderSource(shader, src);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS))
      console.error("Shader:", gl.getShaderInfoLog(shader));
  }

  _setup(fragSrc) {
    const gl = this.gl;
    this.vs = gl.createShader(gl.VERTEX_SHADER);
    this.fs = gl.createShader(gl.FRAGMENT_SHADER);
    this.prog = gl.createProgram();
    this._compile(this.vs, VERT_SHADER);
    this._compile(this.fs, fragSrc);
    gl.attachShader(this.prog, this.vs);
    gl.attachShader(this.prog, this.fs);
    gl.linkProgram(this.prog);
    if (!gl.getProgramParameter(this.prog, gl.LINK_STATUS))
      console.error("Program:", gl.getProgramInfoLog(this.prog));
  }

  _init() {
    const gl = this.gl;
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,1,-1,-1,1,1,1,-1]), gl.STATIC_DRAW);
    const pos = gl.getAttribLocation(this.prog, "position");
    gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);
    this.u = {
      resolution: gl.getUniformLocation(this.prog, "resolution"),
      time:       gl.getUniformLocation(this.prog, "time"),
      u_color:    gl.getUniformLocation(this.prog, "u_color"),
    };
  }

  resize() {
    const dpr = Math.max(1, window.devicePixelRatio);
    this.canvas.width  = window.innerWidth  * dpr;
    this.canvas.height = window.innerHeight * dpr;
    if (this.gl) this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
  }

  setColor(hex) {
    const rgb = hexToRgb(hex);
    if (rgb) this.color = rgb;
  }

  render(now = 0) {
    const { gl, prog, canvas, u } = this;
    if (!gl || !prog || !gl.isProgram(prog)) return;
    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(prog);
    gl.uniform2f(u.resolution, canvas.width, canvas.height);
    gl.uniform1f(u.time, now * 1e-3);
    gl.uniform3fv(u.u_color, this.color);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  destroy() {
    const { gl, prog, vs, fs } = this;
    if (!prog) return;
    if (vs) { gl.detachShader(prog, vs); gl.deleteShader(vs); }
    if (fs) { gl.detachShader(prog, fs); gl.deleteShader(fs); }
    gl.deleteProgram(prog);
  }
}

function SmokeBackground({ smokeColor = "#C8A96E" }) {
  const canvasRef = useRef(null);
  const rendRef   = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rend = new WGLRenderer(canvas, FRAG_SHADER);
    rendRef.current = rend;
    const onResize = () => rend.resize();
    onResize();
    window.addEventListener("resize", onResize);
    let raf;
    const loop = (t) => { rend.render(t); raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return () => { window.removeEventListener("resize", onResize); cancelAnimationFrame(raf); rend.destroy(); };
  }, []);

  useEffect(() => {
    if (rendRef.current) rendRef.current.setColor(smokeColor);
  }, [smokeColor]);

  return <canvas ref={canvasRef} style={{ width: "100%", height: "100%", display: "block" }} />;
}

// ════════════════════════════════════════════════════════════════
//  SVG ICONS (inline — no package required)
// ════════════════════════════════════════════════════════════════

const IconHome = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const IconLayers = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 2 7 12 12 22 7 12 2"/>
    <polyline points="2 17 12 22 22 17"/>
    <polyline points="2 12 12 17 22 12"/>
  </svg>
);

const IconUsers = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 00-3-3.87"/>
    <path d="M16 3.13a4 4 0 010 7.75"/>
  </svg>
);

const IconMail = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
    <polyline points="22,6 12,13 2,6"/>
  </svg>
);

// ════════════════════════════════════════════════════════════════
//  GRADIENT DOCK NAVIGATION
// ════════════════════════════════════════════════════════════════

const NAV_ITEMS = [
  { page: "Home",    label: "Home",    icon: <IconHome />,   from: "#C0A880", to: "#E8DBC8" }, // bleached ash
  { page: "Veneers", label: "Veneers", icon: <IconLayers />, from: "#7A4E28", to: "#C08040" }, // warm walnut
  { page: "About",   label: "About",   icon: <IconUsers />,  from: "#5C4838", to: "#988070" }, // driftwood gray-brown
  { page: "Contact", label: "Contact", icon: <IconMail />,   from: "#7A3020", to: "#C05840" }, // mahogany
];

function GradientDock({ currentPage, onNavigate }) {
  const [hovered, setHovered] = useState(null);

  return (
    <>
      {/* Fixed logo top-left */}
      <div style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 200,
        padding: "18px 32px",
        display: "flex", alignItems: "center",
        pointerEvents: "none",
      }}>
        <button
          onClick={() => { onNavigate("Home"); window.scrollTo(0, 0); }}
          style={{
            background: "none", border: "none", cursor: "pointer", padding: 0,
            pointerEvents: "all",
          }}
        >
          <img
            src="./images/logo.png"
            alt="Walform"
            style={{ height: 300, filter: "brightness(0) invert(1)", display: "block" }}
            onError={(e) => {
              e.target.style.display = "none";
              e.target.nextElementSibling.style.display = "block";
            }}
          />
          <span style={{
            display: "none",
            fontSize: 20, fontFamily: "Georgia,serif", color: C.cream, letterSpacing: "0.05em",
          }}>walform</span>
        </button>
      </div>

      {/* Bottom gradient dock */}
      <nav style={{
        position: "fixed", bottom: 28, left: "50%", transform: "translateX(-50%)",
        zIndex: 200, display: "flex", gap: 10, alignItems: "center",
        padding: "10px 16px",
        background: "rgba(8,6,4,0.88)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        borderRadius: 999,
        border: `1px solid ${C.border}`,
        boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
      }}>
        {NAV_ITEMS.map((item, idx) => {
          const isHov = hovered === idx;
          const isAct = currentPage === item.page;
          const expanded = isHov || isAct;

          return (
            <button
              key={item.page}
              onMouseEnter={() => setHovered(idx)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => { onNavigate(item.page); window.scrollTo(0, 0); }}
              style={{
                position: "relative",
                width: expanded ? 148 : 52,
                height: 52,
                borderRadius: 999,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                overflow: "hidden",
                background: expanded
                  ? `linear-gradient(45deg, ${item.from}, ${item.to})`
                  : "rgba(255,255,255,0.06)",
                transition: "width 0.45s cubic-bezier(0.4,0,0.2,1), background 0.35s ease",
                boxShadow: isHov
                  ? `0 8px 28px ${item.from}55, 0 0 0 1px ${item.from}30`
                  : isAct
                  ? `0 4px 16px ${item.from}33`
                  : "none",
                flexShrink: 0,
              }}
            >
              {/* Glow blur layer */}
              {isHov && (
                <span style={{
                  position: "absolute",
                  inset: 0,
                  borderRadius: 999,
                  background: `linear-gradient(45deg, ${item.from}, ${item.to})`,
                  filter: "blur(12px)",
                  opacity: 0.4,
                  zIndex: -1,
                  transform: "translateY(8px) scaleX(0.85)",
                }} />
              )}
              {/* Icon */}
              <span style={{
                position: "absolute",
                color: expanded ? "white" : "rgba(176,128,96,0.75)",
                display: "flex",
                alignItems: "center",
                transition: "opacity 0.25s, transform 0.25s",
                opacity: expanded ? 0 : 1,
                transform: expanded ? "scale(0.3)" : "scale(1)",
              }}>
                {item.icon}
              </span>
              {/* Label */}
              <span style={{
                position: "absolute",
                color: "white",
                fontSize: 11,
                letterSpacing: "0.13em",
                textTransform: "uppercase",
                fontFamily: "sans-serif",
                fontWeight: 700,
                whiteSpace: "nowrap",
                transition: "opacity 0.2s 0.12s, transform 0.3s 0.08s",
                opacity: expanded ? 1 : 0,
                transform: expanded ? "scale(1)" : "scale(0.6)",
              }}>
                {item.label}
              </span>
            </button>
          );
        })}
      </nav>
    </>
  );
}

// ════════════════════════════════════════════════════════════════
//  PAGE TRANSITION WRAPPER
// ════════════════════════════════════════════════════════════════

function PageFade({ children, id }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 30);
    return () => clearTimeout(t);
  }, [id]);
  return (
    <div style={{ opacity: visible ? 1 : 0, transition: "opacity 0.5s ease" }}>
      {children}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  VENEER SCROLL STORY
// ════════════════════════════════════════════════════════════════

// ── Realistic SVG wood-grain overlay (fine-grain light walnut) ───────────────
// Reference: fine vertical grain, gentle S-curves, warm tan base, subtle
// rosy colour bands — no heavy knots.
function WoodGrainOverlay({ width, height }) {
  // Deterministic RNG — keeps grain stable across re-renders
  const rng = (s) => { const x = Math.sin(s * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

  // ── 1. Vertical tone-variation bands (wide soft columns) ─────────────────
  const bands = Array.from({ length: 10 }, (_, i) => {
    const cx  = (i / 10 + rng(i * 17.3 + 5) * 0.08) * width;
    const bw  = (50 + rng(i * 23.7) * 120);
    const typ = rng(i * 31.1); // 0-0.33 rosy | 0.33-0.66 dark | 0.66-1 light
    const fill =
      typ < 0.33 ? `rgba(190,150,130,0.07)` :   // warm rosy vein area
      typ < 0.66 ? `rgba(120, 85, 55,0.06)` :   // slightly darker stripe
                   `rgba(220,195,170,0.08)`;     // lighter highlight band
    return { cx, bw, fill };
  });

  // ── 2. Broad character streaks (the main visible grain "rivers") ──────────
  const streaks = Array.from({ length: 18 }, (_, i) => {
    const bx  = rng(i * 41.3 + 3) * width;
    const sw  = 1.4 + rng(i * 47.1) * 3.2;        // 1.4 – 4.6 px wide
    const op  = 0.06 + rng(i * 53.9) * 0.11;      // subtle
    // gentle S-curve via two control points that drift horizontally
    const dx1 = (rng(i * 59.3) - 0.5) * 18;
    const dx2 = (rng(i * 61.7) - 0.5) * 18;
    const dx3 = (rng(i * 67.1) - 0.5) * 12;
    const d   = `M ${bx} 0 C ${bx+dx1} ${height*0.28} ${bx+dx2} ${height*0.62} ${bx+dx3} ${height}`;
    // Slightly pinkish-brown on every 3rd streak
    const col = i % 3 === 0 ? "rgba(170,110,80,1)" : "rgba(130,85,50,1)";
    return { d, sw, op, col };
  });

  // ── 3. Dense fine grain lines (the primary detail layer) ─────────────────
  const fineGrain = Array.from({ length: 88 }, (_, i) => {
    const bx  = (i / 88) * width;
    // Each line is a cubic bezier that drifts ± a few px — very tight waviness
    const dx1 = (rng(i * 71.3 + 1) - 0.5) * 7;
    const dx2 = (rng(i * 73.7 + 2) - 0.5) * 7;
    const dxE = (rng(i * 79.1 + 3) - 0.5) * 5;
    const d   = `M ${bx} 0 C ${bx+dx1} ${height*0.3} ${bx+dx2} ${height*0.68} ${bx+dxE} ${height}`;
    const isPrimary = rng(i * 83.3) > 0.72;       // ~28 % are slightly bolder
    const sw  = isPrimary ? 0.7 + rng(i * 89.7) * 0.6 : 0.3;
    const op  = isPrimary ? 0.09 + rng(i * 97.1) * 0.09 : 0.03 + rng(i * 101.3) * 0.03;
    return { d, sw, op };
  });

  // ── 4. Very fine hairlines (adds micro-texture depth) ────────────────────
  const hairlines = Array.from({ length: 55 }, (_, i) => {
    const bx  = rng(i * 107.3 + 9) * width;
    const dx1 = (rng(i * 109.7) - 0.5) * 4;
    const dx2 = (rng(i * 113.1) - 0.5) * 4;
    const d   = `M ${bx} ${rng(i*117.3)*height*0.1} C ${bx+dx1} ${height*0.38} ${bx+dx2} ${height*0.72} ${bx} ${height - rng(i*121.7)*height*0.08}`;
    return { d };
  });

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
    >
      <defs>
        {/* Lateral sheen — brightest on the left-centre, dims to edges */}
        <linearGradient id="vsheen" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%"   stopColor="rgba(240,215,185,0.00)" />
          <stop offset="28%"  stopColor="rgba(250,230,200,0.09)" />
          <stop offset="50%"  stopColor="rgba(255,238,210,0.13)" />
          <stop offset="72%"  stopColor="rgba(245,220,190,0.07)" />
          <stop offset="100%" stopColor="rgba(200,165,130,0.02)" />
        </linearGradient>
      </defs>

      {/* Tone bands */}
      {bands.map((b, i) => (
        <rect key={`b${i}`} x={b.cx - b.bw/2} y={0} width={b.bw} height={height} fill={b.fill} />
      ))}

      {/* Broad character streaks */}
      {streaks.map((s, i) => (
        <path key={`s${i}`} d={s.d} stroke={s.col} strokeWidth={s.sw} fill="none" opacity={s.op} />
      ))}

      {/* Dense fine grain */}
      {fineGrain.map((l, i) => (
        <path key={`f${i}`} d={l.d} stroke="rgba(115,72,38,1)" strokeWidth={l.sw} fill="none" opacity={l.op} />
      ))}

      {/* Hairlines */}
      {hairlines.map((h, i) => (
        <path key={`h${i}`} d={h.d} stroke="rgba(95,58,28,1)" strokeWidth={0.25} fill="none" opacity={0.06} />
      ))}

      {/* Sheen overlay */}
      <rect x={0} y={0} width={width} height={height} fill="url(#vsheen)" />
    </svg>
  );
}

function VeneerScrollStory() {
  const wrapRef  = useRef(null);
  const targetPr = useRef(0);
  const [pr, setPr] = useState(0);

  // RAF-lerp for buttery smooth animation
  useEffect(() => {
    let rafId;
    let current = 0;
    const onScroll = () => {
      const el = wrapRef.current;
      if (!el) return;
      const { top, height } = el.getBoundingClientRect();
      const scrollable = height - window.innerHeight;
      targetPr.current = Math.max(0, Math.min(1, -top / scrollable));
    };
    const tick = () => {
      const diff = targetPr.current - current;
      if (Math.abs(diff) > 0.0004) {
        current += diff * 0.09;        // lerp factor — lower = smoother
        setPr(current);
      }
      rafId = requestAnimationFrame(tick);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    rafId = requestAnimationFrame(tick);
    return () => { window.removeEventListener("scroll", onScroll); cancelAnimationFrame(rafId); };
  }, []);

  // Smooth easing
  const ease = (t) => t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
  // Progress within a segment [a,b], eased 0→1
  const seg = (a, b) => ease(Math.max(0, Math.min(1, (pr - a) / (b - a))));

  // ── Phase 0  (pr 0.00–0.18): veneer face-on, enters ──────────
  // ── Phase 1  (pr 0.18–0.46): rotates to thin edge ───────────
  const rotateIn  = seg(0.18, 0.46) * 82;
  // ── Phase 2  (pr 0.46–0.62): thin strip slides to wall ──────
  const slideRight = seg(0.46, 0.62);       // 0 → 1
  const wallBg     = seg(0.42, 0.66);       // wall fades in
  // ── Phase 3  (pr 0.62–0.76): veneer un-rotates on wall ──────
  const rotateOut  = seg(0.62, 0.76) * 82; // cancels rotation
  const finalRot   = Math.max(0, rotateIn - rotateOut);
  // ── Phase 4  (pr 0.76–0.88): wall panel view ────────────────
  // ── Phase 5  (pr 0.86–1.00): multiple veneers appear ────────
  const multiP     = seg(0.86, 1.0);

  // Veneer horizontal offset: moves toward right-side wall
  const veneerOffsetX = slideRight * 300;

  // Veneer morphs to a large wall-panel shape after sticking
  const stick = seg(0.65, 0.76);
  const panelW = 480 + stick * 120; // 480 → 600  (grows wider when stuck)
  const panelH = 300 + stick * 240; // 300 → 540  (moderately taller)

  // Measurement indicator: visible only while thin
  const measureVis = Math.max(0, seg(0.32, 0.48) - seg(0.50, 0.60));

  // ── Peel / Press / Stick micro-animation ─────────────────────────────────
  // peelRise: corner lifts up
  const peelRise  = seg(0.46, 0.55);
  // pressFlat: corner snaps back flat (slight overshoot)
  const pressFlat = seg(0.55, 0.64);
  // Net corner lift: 0 → max at 0.55 → 0 at 0.64
  const cornerLift = peelRise * (1 - pressFlat);
  const cornerSize = Math.round(cornerLift * 62);   // px — triangle size
  // Lift shadow: strongest when corner is up
  const liftShadow = cornerLift * 28;
  // Press shadow: brief deep press shadow then releases
  const pressShadow = seg(0.56, 0.60) * (1 - seg(0.60, 0.66));
  // Adhesive backing visibility
  const backingVis = cornerLift;

  // Main veneer fades out as multi-veneers take over
  const mainOpacity = 1 - seg(0.90, 1.0);

  // Multiple wall panels, staggered
  const multiPanels = [
    { img: "veneer-10.jpg", bg: "#2E2420", at: 0.86 },
    { img: "veneer-04.jpg", bg: "#7A5E4A", at: 0.90 },
    { img: "veneer-07.jpg", bg: "#9C8878", at: 0.93 },
    { img: "veneer-03.jpg", bg: "#BCA898", at: 0.96 },
  ];

  // Stage label
  const label =
    pr < 0.20 ? { h: "Genuine Wood Veneer",    s: "Real wood. Real character." }
    : pr < 0.50 ? { h: "Sub 1mm Thin",         s: "Thinner than a credit card." }
    : pr < 0.68 ? { h: "Peel. Press. Done.",   s: "Self-adhesive. No infrastructure." }
    : pr < 0.86 ? { h: "Adheres to the wall.", s: "Paint · glass · MDF · tile — anything smooth." }
    :             { h: "Transform any space.",  s: "14+ finishes. Endless possibilities." };

  return (
    <div ref={wrapRef} style={{ height: "480vh", position: "relative" }}>
      <div style={{
        position: "sticky", top: 0, height: "100vh",
        overflow: "hidden", background: C.bg,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>

        {/* ── Wall background (warm white plaster) ── */}
        <div style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(160deg, #F8F4EF 0%, #EDE8E1 55%, #E6E0D8 100%)",
          opacity: wallBg,
        }}>
          {/* Edge vignette for depth */}
          <div style={{
            position: "absolute", inset: 0,
            background: "radial-gradient(ellipse 120% 100% at 50% 50%, transparent 55%, rgba(180,160,140,0.18) 100%)",
          }} />
          {/* Subtle horizontal plaster lines */}
          {[...Array(9)].map((_, i) => (
            <div key={i} style={{
              position: "absolute", left: 0, right: 0,
              top: `${8 + i * 10}%`, height: 1,
              background: "rgba(160,138,118,0.09)",
            }} />
          ))}
          {/* Faint vertical seam lines */}
          {[25, 50, 75].map((x, i) => (
            <div key={i} style={{
              position: "absolute", top: 0, bottom: 0,
              left: `${x}%`, width: 1,
              background: "rgba(160,138,118,0.06)",
            }} />
          ))}
        </div>

        {/* ── Multiple wall veneers (phase 5) ── */}
        <div style={{
          position: "absolute",
          right: "8%", top: "8%", bottom: "8%",
          display: "flex", gap: 6, alignItems: "stretch",
          opacity: multiP,
          zIndex: 6,
        }}>
          {multiPanels.map((v, i) => {
            const vis = seg(v.at, v.at + 0.05);
            return (
              <div key={i} style={{
                width: 110, flexShrink: 0,
                backgroundImage: `url('./images/${v.img}')`,
                backgroundSize: "cover", backgroundPosition: "center",
                backgroundColor: v.bg,
                opacity: vis,
                transform: `translateY(${(1 - vis) * 36}px)`,
              }} />
            );
          })}
        </div>

        {/* ── Main veneer panel ── */}
        <div style={{
          position: "absolute",
          left: "50%", top: "50%",
          transform: `translate(calc(-50% + ${veneerOffsetX}px), -50%)`,
          zIndex: 10,
          opacity: mainOpacity,
        }}>
          {/* Adhesive backing (shows beneath peeling corner) */}
          {backingVis > 0.01 && (
            <div style={{
              position: "absolute", bottom: -4, right: -4,
              width: panelW, height: panelH,
              background: "linear-gradient(135deg,#E8DDC8 0%,#D4C8A8 100%)",
              borderRadius: 2,
              opacity: backingVis * 0.9,
              zIndex: 0,
            }}>
              {/* Backing texture dots */}
              {[...Array(12)].map((_, i) => (
                <div key={i} style={{
                  position: "absolute",
                  left: `${8 + (i % 4) * 24}%`, top: `${10 + Math.floor(i / 4) * 32}%`,
                  width: 3, height: 3, borderRadius: "50%",
                  background: "rgba(140,110,70,0.4)",
                }} />
              ))}
              <p style={{
                position: "absolute", bottom: 10, left: 12,
                fontSize: 8, letterSpacing: "0.15em", textTransform: "uppercase",
                color: "rgba(100,70,40,0.6)", fontFamily: "sans-serif", margin: 0,
              }}>SELF-ADHESIVE BACKING</p>
            </div>
          )}

          {/* Main veneer face */}
          <div style={{
            width: panelW, height: panelH,
            backgroundImage: "url('./images/veneer-04.jpg')",
            backgroundSize: "cover", backgroundPosition: "center",
            backgroundColor: "#C8B49A",   // light walnut tan (matches reference)
            transform: `perspective(1000px) rotateX(${finalRot}deg)`,
            transformOrigin: "50% 50%",
            boxShadow: finalRot > 55
              ? "0 2px 32px rgba(0,0,0,0.9)"
              : pressShadow > 0.05
                ? `0 ${4 + pressShadow * 50}px ${12 + pressShadow * 60}px rgba(0,0,0,${0.6 + pressShadow * 0.3})`
                : `0 ${20 + stick * 40 + liftShadow}px ${60 + stick * 40 + liftShadow * 2}px rgba(0,0,0,${0.45 + cornerLift * 0.35})`,
            position: "relative", overflow: "visible",
            zIndex: 1,
          }}>
            {/* Clip the visual overflow */}
            <div style={{ position: "absolute", inset: 0, overflow: "hidden", borderRadius: 1 }}>
              {/* Wood grain overlay */}
              <WoodGrainOverlay width={panelW} height={panelH} />
              {/* Subtle sheen highlight — left-to-right like a side light source */}
              <div style={{
                position: "absolute", inset: 0,
                background: "linear-gradient(100deg, rgba(255,242,220,0.08) 0%, rgba(255,238,210,0.16) 35%, rgba(240,220,195,0.06) 65%, rgba(180,140,100,0.10) 100%)",
              }} />
            </div>

            {/* ── Peeling corner ── */}
            {cornerSize > 1 && (
              <div style={{
                position: "absolute", bottom: 0, right: 0,
                width: cornerSize, height: cornerSize,
                zIndex: 20, pointerEvents: "none",
                overflow: "visible",
              }}>
                {/* Curl shadow under the lifted corner */}
                <div style={{
                  position: "absolute", bottom: 0, right: 0,
                  width: cornerSize + 10, height: cornerSize + 10,
                  background: `radial-gradient(circle at bottom right, rgba(0,0,0,${0.35 + cornerLift * 0.25}) 0%, transparent 75%)`,
                  transform: "translate(4px, 4px)",
                }} />
                {/* The peel triangle — CSS clip-path fold */}
                <div style={{
                  position: "absolute", bottom: 0, right: 0,
                  width: cornerSize, height: cornerSize,
                  background: "linear-gradient(135deg, #D4C8A8 30%, #C0B090 100%)",
                  clipPath: "polygon(100% 0%, 100% 100%, 0% 100%)",
                  transform: `perspective(200px) rotateY(${-cornerLift * 40}deg) rotateX(${cornerLift * 35}deg)`,
                  transformOrigin: "bottom right",
                }} />
              </div>
            )}
          </div>

          {/* Press ripple flash */}
          {pressShadow > 0.1 && (
            <div style={{
              position: "absolute", inset: -8,
              borderRadius: 3,
              boxShadow: `inset 0 0 ${20 * pressShadow}px rgba(139,96,64,${0.4 * pressShadow})`,
              pointerEvents: "none", zIndex: 15,
            }} />
          )}
        </div>

        {/* ── < 1mm measurement indicator ── */}
        <div style={{
          position: "absolute",
          left: "calc(50% + 258px)", top: "50%",
          transform: "translateY(-50%)",
          opacity: Math.max(0, measureVis),
          display: "flex", alignItems: "center", gap: 14,
          pointerEvents: "none", zIndex: 20,
        }}>
          {/* bracket */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0 }}>
            <div style={{ width: 18, height: 1, background: C.brown }} />
            <div style={{ width: 1, height: 44, background: C.brown }} />
            <div style={{ width: 18, height: 1, background: C.brown }} />
          </div>
          <div>
            <p style={{
              fontSize: 30, fontFamily: "Georgia,serif", margin: 0, lineHeight: 1,
              color: `rgb(${Math.round(242 - wallBg * 200)}, ${Math.round(237 - wallBg * 213)}, ${Math.round(228 - wallBg * 212)})`,
            }}>
              {"< 1mm"}
            </p>
            <p style={{ ...T.label, marginTop: 6, fontSize: 10 }}>thickness</p>
          </div>
        </div>

        {/* ── Stage label (left column, vertically centered) ── */}
        <div style={{
          position: "absolute",
          left: "6%", top: "50%",
          transform: "translateY(-50%)",
          maxWidth: 300,
          textAlign: "left",
          pointerEvents: "none", zIndex: 20,
        }}>
          <p style={{
            ...T.label,
            marginBottom: 12,
            color: `rgb(${Math.round(139 + wallBg * 14)}, ${Math.round(96 - wallBg * 16)}, ${Math.round(64 - wallBg * 16)})`,
          }}>{label.s}</p>
          <h2 style={{
            ...T.h2,
            fontSize: "clamp(22px,2.8vw,42px)",
            color: `rgb(${Math.round(242 - wallBg * 200)}, ${Math.round(237 - wallBg * 213)}, ${Math.round(228 - wallBg * 212)})`,
          }}>{label.h}</h2>
        </div>

        {/* ── Progress dots (right edge) ── */}
        <div style={{
          position: "absolute", right: 28, top: "50%",
          transform: "translateY(-50%)",
          display: "flex", flexDirection: "column", gap: 10, zIndex: 20,
        }}>
          {[0, 0.2, 0.46, 0.65, 0.86].map((t, i) => (
            <div key={i} style={{
              width: 5, height: 5, borderRadius: "50%",
              background: pr >= t + 0.06 ? C.brown : "rgba(139,96,64,0.2)",
              transition: "background 0.4s",
            }} />
          ))}
        </div>

        {/* ── Scroll hint (only at very start) ── */}
        {pr < 0.06 && (
          <div style={{
            position: "absolute", bottom: "5%", left: "50%",
            transform: "translateX(-50%)",
            display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
            opacity: 0.5,
          }}>
            <p style={{ ...T.label, fontSize: 9 }}>scroll to explore</p>
            <div style={{
              width: 1, height: 32,
              background: `linear-gradient(to bottom, transparent, ${C.brownLight})`,
              animation: "scrollPulse 2s ease-in-out infinite",
            }} />
          </div>
        )}
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  HOME PAGE
// ════════════════════════════════════════════════════════════════

function HomePage({ onNavigate }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { const t = setTimeout(() => setMounted(true), 200); return () => clearTimeout(t); }, []);

  return (
    <div>
      {/* HERO — WebGL Smoke */}
      <section style={{ height: "100vh", position: "relative", overflow: "hidden" }}>
        {/* Smoke canvas */}
        <div style={{ position: "absolute", inset: 0, zIndex: 0 }}>
          <SmokeBackground smokeColor="#6B5438" />
        </div>

        {/* Dark vignette overlay */}
        <div style={{
          position: "absolute", inset: 0, zIndex: 1,
          background: "radial-gradient(ellipse at center, rgba(12,9,8,0.25) 0%, rgba(12,9,8,0.72) 100%)",
        }} />
        <div style={{
          position: "absolute", inset: 0, zIndex: 1,
          background: "linear-gradient(to top, rgba(12,9,8,1) 0%, transparent 42%)",
        }} />

        {/* Hero text — centered */}
        <div style={{
          position: "absolute", inset: 0, zIndex: 2,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          textAlign: "center", padding: "0 32px",
        }}>
          <p style={{
            ...T.label,
            marginBottom: 32,
            opacity: mounted ? 1 : 0,
            transform: mounted ? "translateY(0)" : "translateY(12px)",
            transition: "opacity 0.8s 0.2s, transform 0.8s 0.2s",
          }}>
            Walform Surfaces · Mumbai
          </p>

          <h1 style={{
            ...T.h1,
            marginBottom: 24,
            opacity: mounted ? 1 : 0,
            transform: mounted ? "translateY(0)" : "translateY(18px)",
            transition: "opacity 0.9s 0.35s, transform 0.9s 0.35s",
          }}>
            Rome,<br />
            <span style={{ color: C.brownLight }}>Built in</span><br />
            a Day.
          </h1>

          <p style={{
            ...T.body,
            fontSize: 18, maxWidth: 480, marginBottom: 48,
            opacity: mounted ? 1 : 0,
            transform: mounted ? "translateY(0)" : "translateY(14px)",
            transition: "opacity 0.9s 0.5s, transform 0.9s 0.5s",
          }}>
            Ultra-thin real wood veneers under 1mm. Self-adhesive. No ply, no grids, no mess.
          </p>

          <div style={{
            display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center",
            opacity: mounted ? 1 : 0,
            transform: mounted ? "translateY(0)" : "translateY(10px)",
            transition: "opacity 0.9s 0.65s, transform 0.9s 0.65s",
          }}>
            <GoldButton onClick={() => { onNavigate("Veneers"); window.scrollTo(0, 0); }}>
              Explore Veneers
            </GoldButton>
            <OutlineButton onClick={() => { onNavigate("About"); window.scrollTo(0, 0); }}>
              Our Story
            </OutlineButton>
          </div>
        </div>

        {/* Scroll cue */}
        <div style={{
          position: "absolute", bottom: 100, left: "50%", transform: "translateX(-50%)",
          zIndex: 2, display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
          opacity: mounted ? 0.5 : 0, transition: "opacity 1s 1.2s",
        }}>
          <div style={{
            width: 1, height: 48, background: `linear-gradient(to bottom, transparent, ${C.brownLight})`,
            animation: "scrollPulse 2s ease-in-out infinite",
          }} />
        </div>
      </section>

      {/* ── Scroll story ── */}
      <VeneerScrollStory />

      {/* Product teaser */}
      <section style={{ padding: "100px 40px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 48, flexWrap: "wrap", gap: 24 }}>
            <div>
              <p style={{ ...T.label, marginBottom: 14 }}>The Collection</p>
              <h2 style={T.h2}>Crafted in every<br />shade of wood.</h2>
            </div>
            <button
              onClick={() => { onNavigate("Veneers"); window.scrollTo(0, 0); }}
              style={{ background: "none", border: "none", cursor: "pointer", color: C.brownLight, fontSize: 13, letterSpacing: "0.12em", textTransform: "uppercase", fontFamily: "sans-serif", textDecoration: "underline", textUnderlineOffset: 4 }}
            >View All →</button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 3 }}>
            {VENEERS.slice(0, 4).map((v) => (
              <HoverVeneerTile key={v.id} v={v} onClick={() => { onNavigate("Veneers"); window.scrollTo(0, 0); }} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: "100px 40px", background: C.bgAlt, borderTop: `1px solid ${C.border}`, textAlign: "center" }}>
        <p style={{ ...T.label, marginBottom: 24 }}>Get in Touch</p>
        <h2 style={{ ...T.h2, maxWidth: 520, margin: "0 auto 36px" }}>Ready to transform your space?</h2>
        <GoldButton onClick={() => { onNavigate("Contact"); window.scrollTo(0, 0); }}>Contact Us</GoldButton>
      </section>
    </div>
  );
}

function HoverVeneerTile({ v, onClick }) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        aspectRatio: "3/4", cursor: "pointer", position: "relative", overflow: "hidden",
        backgroundImage: `url('./images/${v.file}')`, backgroundSize: "cover", backgroundPosition: "center",
        backgroundColor: v.bg,
        transform: hov ? "scale(1.02)" : "scale(1)",
        transition: "transform 0.5s ease",
      }}
    >
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(to top, rgba(0,0,0,0.75) 0%, transparent 50%)",
        opacity: hov ? 1 : 0.7, transition: "opacity 0.4s",
      }} />
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, padding: "28px 18px 18px" }}>
        <p style={{ ...T.label, fontSize: 9, marginBottom: 4 }}>{v.finish}</p>
        <p style={{ fontSize: 15, color: C.cream, fontFamily: "Georgia,serif", margin: 0 }}>{v.name}</p>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  VENEERS PAGE
// ════════════════════════════════════════════════════════════════

function VeneersPage() {
  const [filter, setFilter] = useState("All");
  const filtered = filter === "All" ? VENEERS : VENEERS.filter((v) => v.tone === filter);

  return (
    <div style={{ paddingTop: 72 }}>
      <div style={{ padding: "80px 40px 56px", background: C.bgAlt, borderBottom: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <p style={{ ...T.label, marginBottom: 18 }}>The Collection</p>
          <h1 style={{ ...T.h2, marginBottom: 20 }}>Our Veneers</h1>
          <p style={{ ...T.body, maxWidth: 520 }}>
            Every panel is a statement. Each veneer is under 1mm thin, self-adhesive, and available in a curated palette of natural wood tones.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 36, flexWrap: "wrap" }}>
            {["All", "Light", "Medium", "Dark"].map((t) => (
              <button key={t} onClick={() => setFilter(t)} style={{
                padding: "8px 20px",
                background: filter === t ? C.brown : "transparent",
                color: filter === t ? C.cream : C.muted,
                border: `1px solid ${filter === t ? C.brown : C.border}`,
                cursor: "pointer", fontSize: 11, letterSpacing: "0.12em",
                textTransform: "uppercase", fontFamily: "sans-serif",
                transition: "all 0.3s", fontWeight: filter === t ? 700 : 400,
              }}>{t}</button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ padding: "56px 40px 120px" }}>
        <div style={{
          maxWidth: 1200, margin: "0 auto",
          display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(250px,1fr))", gap: 24,
        }}>
          {filtered.map((v) => <VeneerCard key={v.id} v={v} />)}
        </div>
      </div>

      {/* Specs */}
      <div style={{ background: C.bgAlt, borderTop: `1px solid ${C.border}`, padding: "80px 40px 120px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 72, alignItems: "center" }}>
          <div>
            <p style={{ ...T.label, marginBottom: 18 }}>Technical Specs</p>
            <h2 style={{ ...T.h2, marginBottom: 28 }}>Engineered for the modern wall.</h2>
            <p style={{ ...T.body, marginBottom: 20 }}>
              Precision-sliced to under 1mm, backed with a high-performance pressure-sensitive adhesive that bonds to painted walls, glass, MDF, and most smooth surfaces.
            </p>
            <p style={T.body}>No skilled labor. No infrastructure. A room transformation in hours, not weeks.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
            {[
              ["Thickness",             "< 1 mm"],
              ["Width",                 "Custom cuts available"],
              ["Adhesive",              "Pressure-sensitive"],
              ["Surface Compatibility", "Wall, Glass, MDF, Tile"],
              ["Fire Rating",           "Available on request"],
              ["Finish Options",        "Silk · Raw · Ribbed"],
            ].map(([k, val]) => (
              <div key={k} style={{ padding: "22px", background: C.bg, borderBottom: `1px solid ${C.border}` }}>
                <p style={{ ...T.label, fontSize: 9, marginBottom: 6 }}>{k}</p>
                <p style={{ color: C.cream, fontSize: 14, fontFamily: "sans-serif", margin: 0 }}>{val}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function VeneerCard({ v }) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{ transform: hov ? "translateY(-5px)" : "translateY(0)", transition: "transform 0.35s ease", cursor: "pointer" }}
    >
      <div style={{
        width: "100%", aspectRatio: "4/3", position: "relative", overflow: "hidden",
        backgroundImage: `url('./images/${v.file}')`, backgroundSize: "cover", backgroundPosition: "center",
        backgroundColor: v.bg, marginBottom: 14,
      }}>
        <div style={{
          position: "absolute", inset: 0,
          background: "rgba(0,0,0,0.15)",
          opacity: hov ? 0 : 1, transition: "opacity 0.4s",
        }} />
        <div style={{
          position: "absolute", top: 10, right: 10, padding: "3px 9px",
          background: "rgba(15,13,11,0.75)", backdropFilter: "blur(4px)",
        }}>
          <span style={{ ...T.label, fontSize: 9 }}>{v.finish}</span>
        </div>
        {/* Shimmer overlay on hover */}
        <div style={{
          position: "absolute", inset: 0,
          background: `linear-gradient(135deg, transparent 40%, rgba(176,128,96,0.1) 50%, transparent 60%)`,
          opacity: hov ? 1 : 0,
          transform: hov ? "translateX(0)" : "translateX(-100%)",
          transition: "opacity 0.3s, transform 0.6s ease",
        }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p style={{ fontSize: 15, fontFamily: "Georgia,serif", color: C.cream, margin: "0 0 4px", fontWeight: 400 }}>{v.name}</p>
          <p style={{ ...T.label, fontSize: 9 }}>{v.tone} Tone</p>
        </div>
        <div style={{ width: 28, height: 28, borderRadius: "50%", background: v.bg, border: `2px solid ${C.border}`, flexShrink: 0 }} />
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  ABOUT PAGE
// ════════════════════════════════════════════════════════════════

function AboutPage() {
  return (
    <div style={{ paddingTop: 72 }}>
      <div style={{ padding: "100px 40px 80px", background: C.bgAlt, borderBottom: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, alignItems: "center" }}>
          <div>
            <p style={{ ...T.label, marginBottom: 22 }}>Our Story</p>
            <h1 style={{ ...T.h2 }}>We reimagined what a wall could be.</h1>
          </div>
          <div>
            <p style={{ ...T.body, fontSize: 18, marginBottom: 22 }}>
              Walform Surfaces was born from a simple frustration: beautiful wood interiors were gated behind weeks of construction, skilled labor, and significant cost.
            </p>
            <p style={T.body}>
              We set out to change that. By engineering veneers under 1mm with a professional-grade self-adhesive backing, we eliminated the need for ply substrates, aluminum grids, and everything in between.
            </p>
          </div>
        </div>
      </div>

      <div style={{ padding: "100px 40px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 2fr", gap: 80 }}>
          <div><p style={{ ...T.label }}>The Idea</p></div>
          <div>
            <p style={{ ...T.body, fontSize: 19, marginBottom: 24, color: C.brownLight, fontStyle: "italic", fontFamily: "Georgia,serif" }}>
              "Rome, Built in a Day."
            </p>
            <p style={{ ...T.body, marginBottom: 20 }}>
              We believe transforming your space shouldn't require tearing it apart first. Our veneers are crafted from real wood, sliced to sub-millimeter precision, and backed with adhesive that bonds to almost any smooth surface.
            </p>
            <p style={T.body}>
              What once took a team of craftsmen weeks can now be done by a single person in an afternoon. That's the Walform promise.
            </p>
          </div>
        </div>
      </div>

      {/* Values */}
      <div style={{ background: C.bgAlt, borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}`, padding: "80px 40px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <p style={{ ...T.label, marginBottom: 44 }}>What We Stand For</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 48 }}>
            {[
              { t: "Simplicity",     d: "Every layer of complexity we remove is a day returned to you. We obsess over making installation intuitive." },
              { t: "Authenticity",   d: "We use real wood. No laminates, no foils. Just genuine veneer, engineered for the modern world." },
              { t: "Accessibility",  d: "Luxury interiors shouldn't require a luxury budget. We make premium wood surfaces achievable for all." },
            ].map((val) => (
              <div key={val.t}>
                <h3 style={{ fontSize: 22, fontFamily: "Georgia,serif", color: C.cream, margin: "0 0 14px", fontWeight: 400 }}>{val.t}</h3>
                <p style={T.body}>{val.d}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Founders */}
      <div style={{ padding: "100px 40px 140px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <p style={{ ...T.label, marginBottom: 44 }}>The Team</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 28 }}>
            {FOUNDERS.map((f) => <FounderCard key={f.name} f={f} />)}
          </div>
          <p style={{ ...T.body, textAlign: "center", marginTop: 52, maxWidth: 480, marginLeft: "auto", marginRight: "auto" }}>
            Three founders, one shared conviction: beautiful spaces should be simple to create. Based in Mumbai, building for the world.
          </p>
        </div>
      </div>
    </div>
  );
}

function FounderCard({ f }) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: "48px 32px", border: `1px solid ${hov ? C.brown : C.border}`,
        textAlign: "center", transition: "border-color 0.3s, transform 0.3s",
        transform: hov ? "translateY(-4px)" : "translateY(0)",
        cursor: "default",
      }}
    >
      <div style={{
        width: 72, height: 72, borderRadius: "50%",
        background: hov
          ? `linear-gradient(135deg, #8B6040, #C08060)`
          : "linear-gradient(135deg, #1A1208, #3A2418)",
        margin: "0 auto 22px",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 26, color: hov ? C.cream : C.brown,
        fontFamily: "Georgia,serif",
        transition: "background 0.4s, color 0.4s",
      }}>
        {f.name.charAt(0)}
      </div>
      <h3 style={{ fontSize: 19, fontFamily: "Georgia,serif", color: C.cream, margin: "0 0 8px", fontWeight: 400 }}>{f.name}</h3>
      <p style={{ ...T.label, fontSize: 10 }}>{f.role}</p>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  CONTACT PAGE
// ════════════════════════════════════════════════════════════════

function ContactPage() {
  const [form, setForm]       = useState({ name: "", email: "", message: "" });
  const [sent, setSent]       = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError]     = useState(null);
  const [focus, setFocus]     = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      const res = await fetch(`https://formspree.io/f/${FORMSPREE_ID}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          name:     form.name,
          email:    form.email,
          message:  form.message,
          _replyto: form.email,
          _subject: `Walform inquiry from ${form.name}`,
        }),
      });
      if (res.ok) {
        setSent(true);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data?.errors?.[0]?.message || "Something went wrong — please try again.");
      }
    } catch {
      setError("Network error — please check your connection and try again.");
    } finally {
      setSending(false);
    }
  };

  const inputStyle = (field) => ({
    width: "100%", padding: "14px 16px",
    background: "#111",
    border: `1px solid ${focus === field ? C.brownLight : C.border}`,
    color: C.cream, fontSize: 15, fontFamily: "sans-serif",
    outline: "none", boxSizing: "border-box",
    transition: "border-color 0.3s",
  });

  return (
    <div style={{ paddingTop: 72 }}>
      <div style={{ padding: "100px 40px 72px", background: C.bgAlt, borderBottom: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <p style={{ ...T.label, marginBottom: 18 }}>Get In Touch</p>
          <h1 style={T.h2}>Let's talk surfaces.</h1>
        </div>
      </div>

      <div style={{ padding: "72px 40px 140px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: 80 }}>
          {/* Info */}
          <div>
            <div style={{ marginBottom: 40 }}>
              <p style={{ ...T.label, marginBottom: 10 }}>Email</p>
              <a href="mailto:info@walformsurfaces.com" style={{ color: C.cream, fontSize: 16, fontFamily: "sans-serif", textDecoration: "none", borderBottom: `1px solid ${C.border}`, paddingBottom: 2 }}>
                info@walformsurfaces.com
              </a>
            </div>
            <div style={{ marginBottom: 40 }}>
              <p style={{ ...T.label, marginBottom: 10 }}>Studio</p>
              <p style={{ ...T.body, color: C.cream, fontSize: 15, lineHeight: 1.9 }}>
                Juhu Griha Swapna<br />
                Gulmohar Cross Road No. 4<br />
                JVPD Scheme<br />
                Mumbai – 400049
              </p>
            </div>
            <div>
              <p style={{ ...T.label, marginBottom: 10 }}>Response Time</p>
              <p style={T.body}>We typically respond within 24 hours on business days.</p>
            </div>
          </div>

          {/* Form */}
          {sent ? (
            <div style={{ padding: "64px 48px", border: `1px solid ${C.brownLight}`, textAlign: "center" }}>
              <span style={{ fontSize: 40, color: C.brownLight }}>◈</span>
              <h3 style={{ fontSize: 24, fontFamily: "Georgia,serif", color: C.cream, margin: "24px 0 14px", fontWeight: 400 }}>Message received.</h3>
              <p style={T.body}>We'll be in touch shortly.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 22 }}>
              {[
                { key: "name",  label: "Your Name",      type: "text" },
                { key: "email", label: "Email Address",   type: "email" },
              ].map(({ key, label, type }) => (
                <div key={key}>
                  <label style={{ ...T.label, display: "block", marginBottom: 10 }}>{label}</label>
                  <input
                    type={type}
                    value={form[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    onFocus={() => setFocus(key)}
                    onBlur={() => setFocus(null)}
                    required
                    style={inputStyle(key)}
                  />
                </div>
              ))}
              <div>
                <label style={{ ...T.label, display: "block", marginBottom: 10 }}>Message</label>
                <textarea
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  onFocus={() => setFocus("message")}
                  onBlur={() => setFocus(null)}
                  required rows={6}
                  style={{ ...inputStyle("message"), resize: "vertical" }}
                />
              </div>
              {error && (
                <p style={{
                  color: "#E07070", fontSize: 14, fontFamily: "sans-serif",
                  border: "1px solid rgba(220,80,80,0.3)", padding: "12px 16px",
                  margin: 0,
                }}>
                  {error}
                </p>
              )}
              <GoldButton type="submit">{sending ? "Sending…" : "Send Message"}</GoldButton>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  SHARED BUTTONS
// ════════════════════════════════════════════════════════════════

function GoldButton({ children, onClick, type = "button" }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      type={type}
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: "16px 38px",
        background: hov ? C.brownLight : C.brown,
        color: C.cream, border: "none", cursor: "pointer",
        fontSize: 12, letterSpacing: "0.15em", textTransform: "uppercase",
        fontFamily: "sans-serif", fontWeight: 700,
        transition: "background 0.3s",
        boxShadow: hov ? `0 8px 24px rgba(139,96,64,0.35)` : "none",
      }}
    >{children}</button>
  );
}

function OutlineButton({ children, onClick }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: "16px 38px",
        background: "transparent",
        color: hov ? C.brownLight : C.cream,
        border: `1px solid ${hov ? C.brownLight : C.border}`,
        cursor: "pointer",
        fontSize: 12, letterSpacing: "0.15em", textTransform: "uppercase",
        fontFamily: "sans-serif",
        transition: "color 0.3s, border-color 0.3s",
      }}
    >{children}</button>
  );
}

// ════════════════════════════════════════════════════════════════
//  FOOTER
// ════════════════════════════════════════════════════════════════

function Footer({ onNavigate }) {
  return (
    <footer style={{ background: "#080604", borderTop: `1px solid ${C.border}`, padding: "56px 40px 120px" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr", gap: 60, marginBottom: 52 }}>
          <div>
            <img src="./images/logo.png" alt="Walform" style={{ height: 26, filter: "brightness(0) invert(1)", marginBottom: 14 }}
              onError={(e) => { e.target.style.display = "none"; e.target.nextSibling.style.display = "block"; }} />
            <span style={{ display: "none", fontSize: 18, fontFamily: "Georgia,serif", color: C.cream, marginBottom: 14, letterSpacing: "0.05em" }}>walform</span>
            <p style={{ ...T.body, fontSize: 13 }}>Rome, Built in a Day.<br />Ultra-thin wood veneers for modern interiors.</p>
          </div>
          <div>
            <p style={{ ...T.label, marginBottom: 18 }}>Navigate</p>
            {["Home","Veneers","About","Contact"].map((l) => (
              <button key={l} onClick={() => { onNavigate(l); window.scrollTo(0, 0); }}
                style={{ display: "block", background: "none", border: "none", cursor: "pointer", color: C.muted, fontSize: 14, fontFamily: "sans-serif", padding: "4px 0", textAlign: "left" }}
              >{l}</button>
            ))}
          </div>
          <div>
            <p style={{ ...T.label, marginBottom: 18 }}>Contact</p>
            <a href="mailto:info@walformsurfaces.com" style={{ display: "block", color: C.muted, fontSize: 14, fontFamily: "sans-serif", textDecoration: "none", marginBottom: 10 }}>
              info@walformsurfaces.com
            </a>
            <p style={{ ...T.body, fontSize: 13, lineHeight: 1.7 }}>JVPD Scheme<br />Mumbai – 400049</p>
          </div>
        </div>
        <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 22, display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <p style={{ ...T.body, fontSize: 12 }}>© 2026 Walform Surfaces. All rights reserved.</p>
          <p style={{ ...T.body, fontSize: 12 }}>Mumbai, India</p>
        </div>
      </div>
    </footer>
  );
}

// ════════════════════════════════════════════════════════════════
//  APP
// ════════════════════════════════════════════════════════════════

export default function WalformSurfaces() {
  const [page, setPage] = useState("Home");

  const renderPage = () => {
    switch (page) {
      case "Home":    return <HomePage    onNavigate={setPage} />;
      case "Veneers": return <VeneersPage />;
      case "About":   return <AboutPage  />;
      case "Contact": return <ContactPage />;
      default:        return <HomePage    onNavigate={setPage} />;
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.cream, fontFamily: "sans-serif" }}>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: ${C.bg}; }
        ::selection { background: ${C.brown}44; color: ${C.cream}; }
        @keyframes scrollPulse {
          0%, 100% { opacity: 0.3; transform: scaleY(0.6); }
          50%       { opacity: 1;   transform: scaleY(1);   }
        }
        @media (max-width: 768px) {
          .grid-2 { grid-template-columns: 1fr !important; }
          .grid-3 { grid-template-columns: 1fr !important; }
          .grid-4 { grid-template-columns: repeat(2,1fr) !important; }
        }
      `}</style>

      <GradientDock currentPage={page} onNavigate={setPage} />

      <PageFade id={page} key={page}>
        {renderPage()}
      </PageFade>

      <Footer onNavigate={setPage} />
    </div>
  );
}
