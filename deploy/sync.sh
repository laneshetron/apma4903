#!/usr/bin/env bash
# Pull recorded data from the AWS host into ./data_aws (same layout as ./data).
#   deploy/sync.sh [host]   (default: the recorder instance)
set -euo pipefail
HOST=${1:-ec2-user@3.21.102.44}
KEY=${KEY:-kalshi-mm.pem}
mkdir -p data_aws
rsync -az --info=progress2 -e "ssh -i $KEY" "$HOST:/opt/kalshi/data/" data_aws/
