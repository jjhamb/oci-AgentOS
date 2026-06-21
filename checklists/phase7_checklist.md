# Phase 7 Checklist: Frontend Design System + Skeleton (Prompts 19–21)

## After Prompt 19 — Design Tokens
- [ ] tokens.css created with ALL CSS custom properties
- [ ] Brand colors defined (--brand-violet, --brand-cyan, etc.)
- [ ] Agent accent colors defined (--agent-orchestrator, --agent-analyst, etc.)
- [ ] Status colors defined (--status-active, --status-idle, etc.)
- [ ] Typography tokens defined (--font-display, --font-mono, font sizes)
- [ ] Spacing tokens defined (--space-1 through --space-6)
- [ ] Effect tokens defined (--blur-*, --transition-*)
- [ ] No raw hex/pixel/font values in any subsequent file

## After Prompt 20 — Component Primitives
- [ ] components.js created with all factory functions
- [ ] GlassCard() — panel background with glass effect
- [ ] Badge() — supports 'subtle' and 'solid' variants
- [ ] StatCard() — label, value, accent color, subtext, bar
- [ ] ProgressBar() — percentage bar with color
- [ ] ThinBar() — 7-day activity chart bars
- [ ] DonutChart() — canvas-based donut chart
- [ ] All functions use CSS custom properties (var(--*))

## After Prompt 21 — Dashboard Skeleton
- [ ] index.html created with full dashboard shell
- [ ] Fixed nav bar with brand mark (gradient ring + pulsing dot)
- [ ] 5 tab buttons: Overview, Agents, Tasks, Schedule, Content
- [ ] Active tab styled as solid white pill with dark text
- [ ] Status pill on right (pulsing mint dot, "All systems operational")
- [ ] Live 24-hour clock
- [ ] Version badge (v1.0) in nav
- [ ] Tab switching works (click to show/hide panels)
- [ ] No data, no SSE, no API calls — just the visual shell
- [ ] Content tab panel is empty placeholder

## Post-Phase Audit
```
Audit the Frontend Design System build against the original prompt spec. Find:
1. Missing features / incomplete implementations
2. Bugs / broken reactivity / console errors
3. Deviations from design system
4. Data source mismatches

Give me a single copy-paste prompt I can use in a NEW session to fix everything found.
```
