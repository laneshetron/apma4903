#!/usr/bin/env python3
"""Signed one-off call to the Kalshi REST API, for account admin from the host.

    sudo -u kalshi bash -c 'cd /opt/kalshi && set -a && . ./.env && set +a && python3 kalshi_call.py GET /account/limits'
    ... python3 kalshi_call.py POST /account/api_usage_level/upgrade '{}'
"""
import base64, json, os, sys, time, urllib.request
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE = "https://api.elections.kalshi.com/trade-api/v2"
key = serialization.load_pem_private_key(open(os.environ["KALSHI_PRIVATE_KEY_PATH"], "rb").read(), None)
method, path = sys.argv[1], sys.argv[2]
body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
ts = str(int(time.time() * 1000))
msg = (ts + method + "/trade-api/v2" + path.split("?")[0]).encode()
sig = base64.b64encode(key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=hashes.SHA256().digest_size), hashes.SHA256())).decode()
h = {"KALSHI-ACCESS-KEY": os.environ["KALSHI_API_KEY_ID"], "KALSHI-ACCESS-TIMESTAMP": ts, "KALSHI-ACCESS-SIGNATURE": sig, "Content-Type": "application/json"}
r = urllib.request.Request(BASE + path, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
try:
    resp = urllib.request.urlopen(r, timeout=10); raw = resp.read().decode()
    print("HTTP", resp.status, json.dumps(json.loads(raw), indent=1) if raw.strip() else "(empty body)")
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:500])
