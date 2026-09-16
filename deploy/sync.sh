#!/usr/bin/env bash
# Pull recorded data from the AWS host into ./data_aws (same layout as ./data).
#   deploy/sync.sh [host]
# Uses tar over ssh (macOS ships openrsync, which cannot read the host's files
# owned by the kalshi user without sudo anyway).
set -euo pipefail
HOST=${1:-ec2-user@18.218.145.115}
KEY=${KEY:-kalshi-mm.pem}
mkdir -p data_aws
# only fetch files that are missing or have changed size (closed hour files never change)
ssh -i "$KEY" "$HOST" 'sudo find /opt/kalshi/data -type f -name "*.gz" -printf "%P %s\n"' | sort > /tmp/remote_list
( cd data_aws && find . -type f -name '*.gz' -printf '%P %s\n' 2>/dev/null || find . -type f -name '*.gz' -exec stat -f '%N %z' {} \; | sed 's|^\./||' ) | sort > /tmp/local_list
comm -23 /tmp/remote_list /tmp/local_list | cut -d' ' -f1 > /tmp/fetch_list
n=$(wc -l < /tmp/fetch_list | tr -d ' ')
echo "fetching $n files"
[ "$n" -gt 0 ] && ssh -i "$KEY" "$HOST" 'sudo tar -C /opt/kalshi/data -cf - -T -' < /tmp/fetch_list | tar -C data_aws -xf -
du -sh data_aws
