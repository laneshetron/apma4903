# Deployment notes

## Which AZ is Kalshi in?

Kalshi's WS (`external-api-ws.kalshi.com`) and trading (`trading-api.kalshi.com`)
endpoints resolve to EC2 addresses in **us-east-2**; `api.elections.kalshi.com`
is CloudFront. The AZ cannot be read from IP ranges, so measure it:

1. Launch one small instance (t3.micro is fine) in each AZ **ID** — `use2-az1`,
   `use2-az2`, `use2-az3` (Console: subnet's "Availability Zone ID"; the
   `us-east-2a/b/c` names are shuffled per account). Enhanced networking is
   default; nothing else matters for the probe.
2. On each: `curl -O <raw url>/deploy/azprobe.py && python3 azprobe.py -n 100 -o $(hostname).json`
   (~1 minute). It reads its own AZ ID from instance metadata.
3. Copy the three JSON files anywhere and run
   `python3 azprobe.py --merge az1.json az2.json az3.json`.

Reading the matrix:

- `TCP connect min` is the RTT to the load balancer node behind each IP. Each
  IP should be ~0.1-0.3 ms from exactly one AZ and 0.5-1.5 ms from the others;
  that assigns IPs to AZs.
- `TTFB min` adds the LB -> backend hop. The AZ whose fastest WS IP also has
  the lowest TTFB is where the backend lives. If TTFB is flat across AZs while
  TCP is not, the LB is cross-zone: deploy in the AZ of the fastest IP and
  connect to that IP directly (pin it in config, re-resolve periodically).
4. Deploy the collector, spot recorder and later the quoter in the winning AZ;
   keep the instance's IP list for `--resolve`-style pinning.
