#!/usr/bin/env python3
"""Move balance between Kalshi exchange shards (crypto markets live on shard 2).

Run on the host as the kalshi user, from /opt/kalshi (reads .env for credentials):

    sudo -u kalshi bash -c 'cd /opt/kalshi && set -a && . ./.env && set +a && python3 shard_transfer.py 5.00 0 2'

Arguments: amount in dollars, source shard, destination shard. Prints the
balance breakdown before and after.
"""

import base64
import json
import os
import sys
import time
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE = "https://api.elections.kalshi.com/trade-api/v2"
key = serialization.load_pem_private_key(open(os.environ["KALSHI_PRIVATE_KEY_PATH"], "rb").read(), None)


def call(method: str, path: str, body: dict | None = None):
    ts = str(int(time.time() * 1000))
    msg = (ts + method + "/trade-api/v2" + path.split("?")[0]).encode()
    sig = base64.b64encode(key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=hashes.SHA256().digest_size), hashes.SHA256())).decode()
    h = {"KALSHI-ACCESS-KEY": os.environ["KALSHI_API_KEY_ID"], "KALSHI-ACCESS-TIMESTAMP": ts, "KALSHI-ACCESS-SIGNATURE": sig, "Content-Type": "application/json"}
    r = urllib.request.Request(BASE + path, method=method, headers=h, data=json.dumps(body).encode() if body else None)
    try:
        return json.load(urllib.request.urlopen(r, timeout=10))
    except urllib.error.HTTPError as e:
        return {"http": e.code, "body": e.read().decode()[:300]}


amount, src, dst = float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
print("before:", call("GET", "/portfolio/balance")["balance_breakdown"])
print("transfer:", call("POST", "/portfolio/intra_exchange_instance_transfer",
                        {"source": "event_contract", "destination": "event_contract", "amount": int(round(amount * 10000)),
                         "source_exchange_shard": src, "destination_exchange_shard": dst}))
time.sleep(3)
print("after:", call("GET", "/portfolio/balance")["balance_breakdown"])
