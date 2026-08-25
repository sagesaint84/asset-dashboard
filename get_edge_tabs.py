#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import json
import time
import urllib.request

# Start Edge with remote debugging
edge = subprocess.Popen([
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "--headless",
    "--remote-debugging-port=9333",
    "--disable-gpu",
    "http://127.0.0.1:4829/dashboard"
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

time.sleep(2)
try:
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9333/json").read().decode())
    print("Tabs:", tabs)
except Exception as e:
    print("Error getting tabs:", e)
finally:
    edge.terminate()
