import subprocess
import re

out = subprocess.check_output([
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    '--headless',
    '--window-size=1280,800',
    '--dump-dom',
    '--virtual-time-budget=6000',
    'http://127.0.0.1:4829/dashboard'
], encoding='utf-8')

matches = re.findall(r'<div class="heatmap-tile" data-symbol="([^"]+)"[^>]*style="([^"]+)"', out)
print(f"Total rendered tiles: {len(matches)}")
for name, style in matches[:12]:
    print(f"{name:20s} -> {style}")
