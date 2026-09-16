#!/usr/bin/env python3
"""Locate Kalshi's backend AZ from inside us-east-2.

Run on one EC2 instance per availability-zone ID (use2-az1/2/3). For every IP
behind Kalshi's WS and REST hostnames it measures, N times: TCP connect
(RTT to the load balancer), TLS handshake, and time-to-first-byte of a GET
that reaches the backend (RTT via LB to the app). ttfb - tls ~ the extra hop
from the load balancer to the backend; the AZ with the smallest of these for
the fastest IPs is the one to deploy in.

    python3 azprobe.py -n 100 -o az.json      # on each instance
    python3 azprobe.py --merge az1.json az2.json az3.json   # anywhere

Stdlib only (Amazon Linux / Ubuntu python3). No credentials needed: the GETs
return 401/404 from the app, which is enough to time the hop.
"""

import argparse
import json
import socket
import ssl
import statistics as st
import sys
import time
import urllib.request

TARGETS = {
    "external-api-ws.kalshi.com": "/trade-api/ws/v2",
    "trading-api.kalshi.com": "/trade-api/v2/exchange/status",
    "api.elections.kalshi.com": "/trade-api/v2/exchange/status",
}


def az_id() -> str:
    try:
        tok = urllib.request.urlopen(urllib.request.Request(
            "http://169.254.169.254/latest/api/token", method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"}), timeout=2).read().decode()
        return urllib.request.urlopen(urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/placement/availability-zone-id",
            headers={"X-aws-ec2-metadata-token": tok}), timeout=2).read().decode()
    except Exception:
        return "unknown"


def resolve(host: str) -> list[str]:
    return sorted({ai[4][0] for ai in socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)})


def sample(host: str, ip: str, path: str, ctx: ssl.SSLContext) -> tuple[float, float, float]:
    """(tcp_ms, tls_ms, ttfb_ms), each measured from the previous stage."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    t0 = time.perf_counter()
    s.connect((ip, 443))
    t1 = time.perf_counter()
    ss = ctx.wrap_socket(s, server_hostname=host)
    t2 = time.perf_counter()
    ss.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: azprobe\r\nConnection: close\r\n\r\n".encode())
    ss.recv(1)
    t3 = time.perf_counter()
    ss.close()
    return (t1 - t0) * 1e3, (t2 - t1) * 1e3, (t3 - t2) * 1e3


def probe(n: int) -> dict:
    ctx = ssl.create_default_context()
    out = {"az_id": az_id(), "n": n, "results": {}}
    print(f"probing from {out['az_id']}", file=sys.stderr)
    for host, path in TARGETS.items():
        for ip in resolve(host):
            tcp, tls, ttfb = [], [], []
            for _ in range(n):
                try:
                    a, b, c = sample(host, ip, path, ctx)
                except Exception as e:
                    print(f"{host} {ip}: {e}", file=sys.stderr)
                    continue
                tcp.append(a); tls.append(b); ttfb.append(c)
                time.sleep(0.02)
            if not tcp:
                continue
            r = {"host": host, "tcp_p50": st.median(tcp), "tcp_min": min(tcp), "tls_p50": st.median(tls),
                 "ttfb_p50": st.median(ttfb), "ttfb_min": min(ttfb), "n": len(tcp)}
            out["results"][ip] = r
            print(f"{host:28s} {ip:16s} tcp p50 {r['tcp_p50']:.3f} min {r['tcp_min']:.3f}  tls {r['tls_p50']:.2f}  "
                  f"ttfb p50 {r['ttfb_p50']:.3f} min {r['ttfb_min']:.3f} ms", file=sys.stderr)
    return out


def merge(paths: list[str]) -> None:
    runs = [json.load(open(p)) for p in paths]
    azs = [r["az_id"] for r in runs]
    ips = sorted({ip for r in runs for ip in r["results"]}, key=lambda ip: (next(r["results"][ip]["host"] for r in runs if ip in r["results"]), ip))
    for metric, label in (("tcp_min", "TCP connect min (ms) = RTT to the load balancer"),
                          ("ttfb_min", "TTFB min (ms) = RTT via LB to the backend")):
        print(f"\n{label}\n")
        print("| host | ip | " + " | ".join(azs) + " | nearest |")
        print("|---|---|" + "---|" * (len(azs) + 1))
        for ip in ips:
            host = next(r["results"][ip]["host"] for r in runs if ip in r["results"])
            vals = [r["results"].get(ip, {}).get(metric) for r in runs]
            best = min((v, a) for v, a in zip(vals, azs) if v is not None)[1]
            print(f"| {host} | {ip} | " + " | ".join(f"{v:.3f}" if v is not None else "-" for v in vals) + f" | {best} |")
    print("\nPer-AZ best backend RTT (min over WS IPs of ttfb_min):")
    for r in runs:
        ws = [v["ttfb_min"] for v in r["results"].values() if v["host"] == "external-api-ws.kalshi.com"]
        print(f"  {r['az_id']}: {min(ws):.3f} ms" if ws else f"  {r['az_id']}: no WS samples")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=100, help="samples per IP")
    ap.add_argument("-o", default=None, help="write JSON here")
    ap.add_argument("--merge", nargs="+", default=None, help="merge per-AZ JSON files into a matrix")
    a = ap.parse_args()
    if a.merge:
        merge(a.merge)
        return
    out = probe(a.n)
    text = json.dumps(out, indent=1)
    if a.o:
        open(a.o, "w").write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
