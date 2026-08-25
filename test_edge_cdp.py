import asyncio
import json
import subprocess
import time
import urllib.request

# 1. Run msedge with remote debugging port
edge_proc = subprocess.Popen([
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "--headless",
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "http://127.0.0.1:4829"
])
time.sleep(2)

try:
    # 2. Get websocket debugger URL
    res = urllib.request.urlopen("http://127.0.0.1:9222/json")
    tabs = json.loads(res.read().decode())
    ws_url = tabs[0]["webSocketDebuggerUrl"]
    print("WebSocket Debugger URL:", ws_url)
except Exception as e:
    print("Failed to get tabs:", e)
finally:
    edge_proc.terminate()
