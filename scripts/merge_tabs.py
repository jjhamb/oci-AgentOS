#!/usr/bin/env python3
"""Merge standalone tabs into index.html"""
import re
import shutil
from datetime import datetime

# Backup first
ts = datetime.now().strftime('%Y-%m-%dT%H-%M')
shutil.copy2(
    '/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html',
    f'/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backups/index_v2.6_pre_merge_{ts}.html'
)
print(f"Backup created: index_v2.6_pre_merge_{ts}.html")

# Read files
with open('/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html', 'r') as f:
    index_html = f.read()

tab_files = {}
for name in ['tasks', 'schedule', 'content', 'terminal']:
    with open(f'/home/jayant/Desktop/Hermes-AgentOS-Dashboard/tabs/{name}.html', 'r') as f:
        tab_files[name] = f.read()

def extract_panel(html, panel_id):
    """Extract the content of a specific tab-panel div."""
    # Find the panel start - could be "tab-panel active" or just "tab-panel"
    pattern = f'id="{panel_id}"'
    start_idx = html.find(pattern)
    if start_idx == -1:
        return None
    
    # Go back to find the opening <div
    div_start = html.rfind('<div', 0, start_idx)
    if div_start == -1:
        return None
    
    # Now find the matching closing </div>
    depth = 1
    idx = div_start + 4
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
                return html[div_start:next_close + 6].strip()
            idx = next_close + 6
    return None

def extract_scripts(html):
    """Extract all <script>...</script> contents."""
    return re.findall(r'<script>(.*?)</script>', html, re.DOTALL)

# Extract panels
panels = {}
for name in ['tasks', 'schedule', 'content', 'terminal']:
    panel = extract_panel(tab_files[name], f'panel-{name}')
    panels[name] = panel
    print(f"{name} panel: {len(panel) if panel else 'NOT FOUND'} chars")

if not all(panels.values()):
    print("ERROR: Could not extract all panels!")
    # Debug: show what we found
    for name, panel in panels.items():
        if panel:
            print(f"  {name}: starts with: {panel[:100]}")
    exit(1)

# Extract JS
js_blocks = {}
for name in ['tasks', 'schedule', 'content', 'terminal']:
    js = '\n'.join(extract_scripts(tab_files[name]))
    js_blocks[name] = js
    print(f"{name} JS: {len(js)} chars")

# ── 1. Replace placeholder panels in index.html ──
# The placeholders look like:
#   <div class="tab-panel" id="panel-tasks">\n    <div class="glass-card">...\n  </div>

# Tasks
old_tasks = re.search(r'<div class="tab-panel" id="panel-tasks">\s*<div class="glass-card">.*?</div>\s*</div>', index_html, re.DOTALL)
if old_tasks:
    print(f"Found tasks placeholder: {old_tasks.start()}-{old_tasks.end()}")
    index_html = index_html[:old_tasks.start()] + panels['tasks'] + index_html[old_tasks.end():]
else:
    print("WARNING: Could not find tasks placeholder")

# Schedule
old_schedule = re.search(r'<div class="tab-panel" id="panel-schedule">\s*<div class="glass-card">.*?</div>\s*</div>', index_html, re.DOTALL)
if old_schedule:
    print(f"Found schedule placeholder: {old_schedule.start()}-{old_schedule.end()}")
    index_html = index_html[:old_schedule.start()] + panels['schedule'] + index_html[old_schedule.end():]
else:
    print("WARNING: Could not find schedule placeholder")

# Content
old_content = re.search(r'<div class="tab-panel" id="panel-content">\s*<div class="glass-card">.*?</div>\s*</div>', index_html, re.DOTALL)
if old_content:
    print(f"Found content placeholder: {old_content.start()}-{old_content.end()}")
    index_html = index_html[:old_content.start()] + panels['content'] + index_html[old_content.end():]
else:
    print("WARNING: Could not find content placeholder")

# ── 2. Add Terminal tab button ──
if 'data-tab="terminal"' not in index_html:
    index_html = index_html.replace(
        '<button class="tab-btn" data-tab="content">Content</button>',
        '<button class="tab-btn" data-tab="content">Content</button>\n    <button class="tab-btn" data-tab="terminal">Terminal</button>'
    )
    print("Added Terminal tab button")
else:
    print("Terminal tab button already exists")

# ── 3. Add Terminal panel ──
if 'panel-terminal' not in index_html:
    terminal_full = f'<div class="tab-panel" id="panel-terminal">\n{panels["terminal"]}\n</div>'
    # Insert before the scripts section
    script_marker = '\n\n<!-- ═══════════ SCRIPTS ═══════════ -->'
    if script_marker in index_html:
        index_html = index_html.replace(script_marker, f'\n{terminal_full}\n{script_marker}')
        print("Added Terminal panel")
    else:
        print("WARNING: Could not find scripts marker")
else:
    print("Terminal panel already exists")

# ── 4. Update tab switching to lazy-load tabs ──
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
      // Lazy-load tab data on first visit
      const tab = btn.dataset.tab;
      if (tab === 'tasks' && !window._tasksStarted) { window._tasksStarted = true; fetchKanban(); }
      if (tab === 'schedule' && !window._scheduleStarted) { window._scheduleStarted = true; fetchCron(); }
      if (tab === 'content' && !window._contentStarted) { window._contentStarted = true; loadDir('/home/jayant/.hermes/content'); }
      if (tab === 'terminal' && !window._terminalStarted) { window._terminalStarted = true; initTerminal(); }
    });
  });"""

if old_tab_switch in index_html:
    index_html = index_html.replace(old_tab_switch, new_tab_switch)
    print("Updated tab switching with lazy-load hooks")
else:
    print("WARNING: Could not find tab switch block to update")

# ── 5. Add all the new JS before the closing </script> ──
all_new_js = f'''

  // ═══════════════════════════════════════════
  // TASKS TAB
  // ═══════════════════════════════════════════
{js_blocks['tasks']}

  // ═══════════════════════════════════════════
  // SCHEDULE TAB
  // ═══════════════════════════════════════════
{js_blocks['schedule']}

  // ═══════════════════════════════════════════
  // CONTENT TAB
  // ═══════════════════════════════════════════
{js_blocks['content']}

  // ═══════════════════════════════════════════
  // TERMINAL TAB
  // ═══════════════════════════════════════════
{js_blocks['terminal']}
'''

last_script_idx = index_html.rfind('</script>')
if last_script_idx != -1:
    index_html = index_html[:last_script_idx] + all_new_js + '\n' + index_html[last_script_idx:]
    print(f"Added {len(all_new_js)} chars of new JS")
else:
    print("WARNING: Could not find </script> to insert JS")

# Write the merged file
with open('/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html', 'w') as f:
    f.write(index_html)

lines = index_html.count('\n')
print(f"\nMerged index.html: {len(index_html)} chars, {lines} lines")
print("Done!")
