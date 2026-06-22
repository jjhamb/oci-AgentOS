#!/usr/bin/env python3
"""Fix merged index.html — proper extraction of panel inner content only"""
import re
import shutil

# Restore from backup
shutil.copy2(
    '/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backups/index_v2.6_pre_merge_2026-06-22T00-32.html',
    '/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html'
)
print("Restored from clean backup")

with open('/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html', 'r') as f:
    index_html = f.read()

tab_files = {}
for name in ['tasks', 'schedule', 'content', 'terminal']:
    with open(f'/home/jayant/Desktop/Hermes-AgentOS-Dashboard/tabs/{name}.html', 'r') as f:
        tab_files[name] = f.read()

def extract_panel_inner(html, panel_id):
    pattern = f'id="{panel_id}"'
    start_idx = html.find(pattern)
    if start_idx == -1:
        return None
    div_start = html.rfind('<div', 0, start_idx)
    if div_start == -1:
        return None
    tag_end = html.find('>', div_start) + 1
    depth = 1
    idx = tag_end
    while depth > 0 and idx < len(html):
        next_open = html.find('<div', idx)
        next_close = html.find('</div>', idx)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            idx = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                return html[tag_end:next_close].strip()
            idx = next_close + 6
    return None

def extract_scripts(html):
    return re.findall(r'<script>(.*?)</script>', html, re.DOTALL)

panels = {}
for name in ['tasks', 'schedule', 'content', 'terminal']:
    panel = extract_panel_inner(tab_files[name], f'panel-{name}')
    panels[name] = panel
    print(f"{name} inner panel: {len(panel) if panel else 'NOT FOUND'} chars")

if not all(panels.values()):
    print("ERROR: Could not extract all panels!")
    exit(1)

js_blocks = {}
for name in ['tasks', 'schedule', 'content', 'terminal']:
    js = '\n'.join(extract_scripts(tab_files[name]))
    js_blocks[name] = js
    print(f"{name} JS: {len(js)} chars")

# ── 1. Replace placeholder panels ──
for name in ['tasks', 'schedule', 'content']:
    panel_id = f'panel-{name}'
    placeholder_pattern = f'<div class="tab-panel" id="{panel_id}">'
    ph_start = index_html.find(placeholder_pattern)
    if ph_start == -1:
        print(f"WARNING: Could not find placeholder for {panel_id}")
        continue
    
    # Find the end of this panel (matching </div>)
    tag_end = index_html.find('>', ph_start) + 1
    depth = 1
    idx = tag_end
    while depth > 0 and idx < len(index_html):
        next_open = index_html.find('<div', idx)
        next_close = index_html.find('</div>', idx)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            idx = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                ph_end = next_close + 6
                break
            idx = next_close + 6
    
    replacement = f'<div class="tab-panel" id="{panel_id}">\n{panels[name]}\n</div>'
    index_html = index_html[:ph_start] + replacement + index_html[ph_end:]
    print(f"Replaced {name} placeholder")

# ── 2. Add Terminal tab button ──
if 'data-tab="terminal"' not in index_html:
    index_html = index_html.replace(
        '<button class="tab-btn" data-tab="content">Content</button>',
        '<button class="tab-btn" data-tab="content">Content</button>\n    <button class="tab-btn" data-tab="terminal">Terminal</button>'
    )
    print("Added Terminal tab button")

# ── 3. Add Terminal panel before scripts section ──
script_marker = '\n\n<!-- ═══════════ SCRIPTS ═══════════ -->'
if script_marker in index_html:
    terminal_full = f'\n<div class="tab-panel" id="panel-terminal">\n{panels["terminal"]}\n</div>\n'
    index_html = index_html.replace(script_marker, terminal_full + script_marker)
    print("Added Terminal panel")

# ── 4. Update tab switching ──
old_tab_switch = """document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
    });
  });"""

new_tab_switch = """document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
      const tab = btn.dataset.tab;
      if (tab === 'tasks' && !window._tasksStarted) { window._tasksStarted = true; fetchKanban(); }
      if (tab === 'schedule' && !window._scheduleStarted) { window._scheduleStarted = true; fetchCron(); }
      if (tab === 'content' && !window._contentStarted) { window._contentStarted = true; loadDir('/home/jayant/.hermes/content'); }
      if (tab === 'terminal' && !window._terminalStarted) { window._terminalStarted = true; initTerminal(); }
    });
  });"""

if old_tab_switch in index_html:
    index_html = index_html.replace(old_tab_switch, new_tab_switch)
    print("Updated tab switching")
else:
    print("WARNING: Could not find tab switch block")

# ── 5. Add new JS before closing </script> ──
all_new_js = f'''

  // ═══════════════════════════════════════════
  // TASKS TAB (kanban board)
  // ═══════════════════════════════════════════
{js_blocks['tasks']}

  // ═══════════════════════════════════════════
  // SCHEDULE TAB (cron jobs)
  // ═══════════════════════════════════════════
{js_blocks['schedule']}

  // ═══════════════════════════════════════════
  // CONTENT TAB (file browser)
  // ═══════════════════════════════════════════
{js_blocks['content']}

  // ═══════════════════════════════════════════
  // TERMINAL TAB
  // ═══════════════════════════════════════════
{js_blocks['terminal']}
'''

last_script_idx = index_html.rfind('</script>')
if last_script_idx != -1:
    index_html = index_html[:last_script_idx] + all_new_js + index_html[last_script_idx:]
    print(f"Added {len(all_new_js)} chars of JS")

# Write
with open('/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html', 'w') as f:
    f.write(index_html)

# Verify
panels_found = list(re.finditer(r'<div class="tab-panel[^"]*" id="(panel-[a-z]+)"', index_html))
print(f"\nFinal: {len(panels_found)} panels, {index_html.count(chr(10))} lines, {len(index_html)} bytes")
for p in panels_found:
    line_num = index_html[:p.start()].count('\n') + 1
    print(f"  {p.group(1)} at line {line_num}")
