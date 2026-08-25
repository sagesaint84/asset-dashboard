import asyncio
import json
import subprocess
import httpx
import websockets

async def capture_browser_console():
    proc = subprocess.Popen([
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "--headless",
        "--remote-debugging-port=9333",
        "http://127.0.0.1:4829/dashboard"
    ])
    try:
        await asyncio.sleep(2)
        async with httpx.AsyncClient() as client:
            tabs = (await client.get("http://127.0.0.1:9333/json")).json()
            ws_url = tabs[0]["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 2, "method": "Console.enable"}))
            await ws.send(json.dumps({"id": 3, "method": "Page.reload"}))

            end_time = asyncio.get_event_loop().time() + 5.0
            while asyncio.get_event_loop().time() < end_time:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(msg)
                    method = data.get("method")
                    if method == "Runtime.exceptionThrown":
                        details = data.get("params", {}).get("exceptionDetails", {})
                        print("JS EXCEPTION:", details.get("text"), details.get("exception", {}).get("description"))
                    elif method == "Console.messageAdded":
                        print("CONSOLE MSG:", data.get("params", {}).get("message", {}).get("text"))
                except asyncio.TimeoutError:
                    pass
    finally:
        proc.terminate()

asyncio.run(capture_browser_console())
