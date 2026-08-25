#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import subprocess
import time
import urllib.request

async def capture():
    edge = subprocess.Popen([
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "--headless",
        "--remote-debugging-port=9444",
        "--disable-gpu",
        "http://127.0.0.1:4829/dashboard"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    
    try:
        tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9444/json").read().decode())
        page_tab = [t for t in tabs if t.get("type") == "page"][0]
        ws_url = page_tab["webSocketDebuggerUrl"]
        print("Connecting to:", ws_url)
        
        # Connect with pure asyncio websocket or sockets
        import websockets
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 2, "method": "Console.enable"}))
            await ws.send(json.dumps({"id": 3, "method": "Page.reload"}))
            
            for _ in range(30):
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                method = data.get("method", "")
                if "exception" in method.lower() or "console" in method.lower():
                    print("CDP EVENT:", json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        print("CDP Error:", e)
    finally:
        edge.terminate()

asyncio.run(capture())
