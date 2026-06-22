#!/usr/bin/env python3
"""Fix merged index.html — remove active class from merged panels and fix nested divs"""
import re

with open('/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html', 'r') as f:
    html = f.read()

# Fix: Remove "active" class from all tab-panel divs except panel-overview
# The merged panels have: <div class="tab-panel active" id="panel-tasks">
# They should be: <div class="tab-panel" id="panel-tasks">

# Replace active class on non-overview panels
for panel in ['panel-tasks', 'panel-schedule', 'panel-content', 'panel-terminal']:
    # Replace the first occurrence (the actual panel, not any nested content)
    html = html.replace(
        f'<div class="tab-panel active" id="{panel}">',
        f'<div class="tab-panel" id="{panel}">',
        1  # Only replace first occurrence
    )

# Fix: Remove duplicate panel-terminal (the nested one)
# Find the pattern: <div class="tab-panel" id="panel-terminal">\n<div class="tab-panel active" id="panel-terminal">
# and remove the outer wrapper, keeping only the inner content
# Actually, let's find and remove the duplicate
idx1 = html.find('<div class="tab-panel" id="panel-terminal">')
if idx1 != -1:
    idx2 = html.find('<div class="tab-panel active" id="panel-terminal">', idx1 + 1)
    if idx2 != -1 and idx2 - idx1 < 10:
        # They're adjacent — remove the first (outer) one
        # Find the end of the first opening tag
        tag_end = html.find('>', idx1) + 1
        # Find the closing </div> of the inner panel
        # We need to find the matching close for the inner panel
        inner_start = idx2
        depth = 1
        idx = inner_start + 4
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
                    # Remove from idx1 to next_close + 6
                    html = html[:idx1] + html[next_close + 6:]
                    print(f"Removed duplicate panel-terminal wrapper at {idx1}")
                    break
                idx = next_close + 6

# Same fix for other panels — check if they have nested duplicates
for panel in ['panel-tasks', 'panel-schedule', 'panel-content']:
    pattern = f'<div class="tab-panel" id="{panel}">'
    idx1 = html.find(pattern)
    if idx1 != -1:
        # Check if right after it there's another tab-panel with active
        after = html[idx1 + len(pattern):idx1 + len(pattern) + 80]
        if 'tab-panel active' in after and panel in after:
            # Remove the outer wrapper
            tag_end = html.find('>', idx1) + 1
            # Find the inner panel
            inner_pattern = f'<div class="tab-panel active" id="{panel}">'
            inner_idx = html.find(inner_pattern, idx1 + len(pattern))
            if inner_idx != -1 and inner_idx - idx1 < 10:
                # Find closing of inner panel
                depth = 1
                idx = inner_idx + 4
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
                            html = html[:idx1] + html[next_close + 6:]
                            print(f"Removed duplicate {panel} wrapper")
                            break
                        idx = next_close + 6

with open('/home/jayant/Desktop/Hermes-AgentOS-Dashboard/backend/index.html', 'w') as f:
    f.write(html)

# Verify
panels = list(re.finditer(r'<div class="tab-panel[^"]*" id="(panel-[a-z]+)"', html))
print(f"\nPanels after fix: {len(panels)}")
for p in panels:
    line_num = html[:p.start()].count('\n') + 1
    print(f"  {p.group(1)} at line {line_num}")

print(f"Total: {html.count(chr(10))} lines, {len(html)} bytes")
