#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cdp_capture_errors.py
Launch headless Edge with remote debugging and capture all console.error / runtime exceptions
"""
import subprocess
import time
import json
import urllib.request
import asyncio
import socket

# Check for websocket client
try:
    import websockets
except ImportError:
    # Use standard library socket or install
    pass

print("Testing simple HTTP fetch of http://127.0.0.1:4829/ ...")
req = urllib.request.Request("http://127.0.0.1:4829/")
try:
    resp = urllib.request.urlopen(req)
    print("HTTP Status:", resp.status)
    print("HTTP Headers:", dict(resp.headers))
except Exception as e:
    print("HTTP Error:", e)
