#!/usr/bin/env python3
"""Verify merged index.html structure"""
import re

with open('/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html') as f:
    html = f.read()

# Find all tab-panel divs
panels = list(re.finditer(r'<div class="tab-panel[^"]*" id="(panel-[a-z]+)"', html))
print("Tab panels found:")
for p in panels:
    line_num = html[:p.start()].count('\n') + 1
    print(f"  {p.group(1)} at line {line_num}")

# Check for the closing structure
print(f"\nTotal lines: {html.count(chr(10))}")
print(f"Size: {len(html)} bytes")

# Check key JS functions exist
for fn in ['fetchKanban', 'fetchCron', 'loadDir', 'initTerminal', 'renderOverview', 'renderAgentsTab']:
    found = fn in html
    print(f"  JS function {fn}: {'OK' if found else 'MISSING'}")

# Check tab buttons
for tab in ['overview', 'agents', 'tasks', 'schedule', 'content', 'terminal']:
    found = f'data-tab="{tab}"' in html
    print(f"  Tab button {tab}: {'OK' if found else 'MISSING'}")
