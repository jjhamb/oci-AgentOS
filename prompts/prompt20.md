# Prompt 20 — Component Primitives (Reusable Building Blocks)

**Phase:** 7 (Frontend Design System)
**Send to:** Coder

---

Create `components.js` exporting tiny factory functions. All tabs import from here — no duplicate markup logic.

export const GlassCard = ({ children, className = '', style = {} }) => `
  <div class="glass-card ${className}" style="
    background: var(--bg-glass);
    backdrop-filter: var(--blur-heavy);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    ${Object.entries(style).map(([k,v]) => `${k}: ${v};`).join(' ')}
  ">${children}</div>
`;

export const Badge = ({ text, color = 'var(--text-muted)', variant = 'subtle' }) => {
  const bg = variant === 'solid' ? color : `${color}20`;
  return `<span class="badge" style="
    background: ${bg};
    color: ${color};
    border: ${variant === 'solid' ? 'none' : `1px solid ${color}40`};
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-full);
    font: 500 var(--font-size-xs) var(--font-mono);
    letter-spacing: var(--letter-spacing-wide);
    text-transform: uppercase;
  ">${text}</span>`;
};

export const StatCard = ({ label, value, accent, subtext, barWidth = '100%' }) => `
  <div class="stat-card" style="background: var(--bg-glass); backdrop-filter: var(--blur-heavy); border: 1px solid var(--border-glass); border-radius: var(--radius-lg); padding: var(--space-4); position: relative;">
    <div style="font: 400 var(--font-size-xs) var(--font-mono); color: var(--text-muted); letter-spacing: var(--letter-spacing-wide); text-transform: uppercase;">${label}</div>
    <div style="font: 700 var(--font-size-2xl) var(--font-display); color: ${accent};">${value}</div>
    ${subtext ? `<div style="font: 400 var(--font-size-sm) var(--font-mono); color: var(--text-muted); margin-top: var(--space-1);">${subtext}</div>` : ''}
    <div style="position: absolute; bottom: 0; left: 0; height: 2px; width: ${barWidth}; background: ${accent}; border-radius: var(--radius-full);"></div>
  </div>
`;

export const ProgressBar = ({ pct, color = 'var(--brand-cyan)', height = '6px' }) => `
  <div style="background: rgba(255,255,255,0.05); border-radius: var(--radius-full); height: ${height}; overflow: hidden;">
    <div style="height: 100%; width: ${pct}%; background: ${color}; border-radius: var(--radius-full); transition: width var(--transition-normal);"></div>
  </div>
`;

export const ThinBar = ({ pct, color }) => `
  <div style="display: flex; gap: 2px; align-items: flex-end; height: 32px;">
    ${pct.reverse().map((v, i) => `<div style="width: calc(100% / 7 - 2px); height: ${Math.max(2, v * 0.32)}px; background: ${color}; border-radius: var(--radius-sm); opacity: ${v > 0 ? 0.85 : 0.15};"></div>`).join('')}
  </div>
`;

export const DonutChart = ({ slices, total }) => {
  if (total === 0) return '<canvas style="width:130px;height:130px"></canvas>';
  let currentAngle = -Math.PI / 2;
  return `<canvas style="width:130px;height:130px" data-slices='${JSON.stringify(slices)}' data-total='${total}' data-current='${currentAngle}'></canvas>`;
};

---

## What to Watch For
- These are JavaScript factory functions that return HTML strings
- All functions must use CSS custom properties (var(--*)) — no raw values
- GlassCard is the primary panel wrapper used everywhere
- Badge supports 'subtle' and 'solid' variants
- DonutChart renders to a canvas element (drawn by JS later)
