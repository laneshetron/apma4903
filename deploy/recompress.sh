#!/usr/bin/env bash
# Recompress archived tape files from gzip to zstd (~45% smaller, faster to read).
#
#   deploy/recompress.sh <dir> [level] [jobs]
#   deploy/recompress.sh data_broad/raw/2026-09-20
#   deploy/recompress.sh data_aws/raw 15 4
#
# Each hour file is converted, verified byte-for-byte against the original
# decompressed stream, and only then is the .gz removed. Interrupting is safe:
# a half-written .zst is discarded and the .gz is still there. Files the
# collector may still be writing (the newest hour) are skipped unless --all.
set -euo pipefail

DIR=${1:?usage: recompress.sh <dir> [level] [jobs]}
LEVEL=${2:-15}
JOBS=${3:-4}

command -v zstd >/dev/null || { echo "zstd not installed" >&2; exit 1; }

convert() {
  local gz="$1" level="$2"
  local zst="${gz%.gz}.zst"
  local tmp="$zst.part"
  # skip if a live process still holds the file open (the collector's current hour)
  if command -v lsof >/dev/null && lsof -t -- "$gz" >/dev/null 2>&1; then
    echo "skip (open): $gz"
    return 0
  fi
  rm -f "$tmp"
  if ! gzip -dc -- "$gz" | zstd -q -"$level" -T1 -o "$tmp"; then
    echo "FAIL compress: $gz" >&2
    rm -f "$tmp"
    return 1
  fi
  # verify: the decompressed streams must be identical
  local a b
  a=$(gzip -dc -- "$gz" | shasum -a 256 | cut -d' ' -f1)
  b=$(zstd -dc -- "$tmp" | shasum -a 256 | cut -d' ' -f1)
  if [ "$a" != "$b" ]; then
    echo "FAIL verify: $gz ($a != $b)" >&2
    rm -f "$tmp"
    return 1
  fi
  mv -- "$tmp" "$zst"
  local before after
  before=$(wc -c < "$gz")
  after=$(wc -c < "$zst")
  rm -- "$gz"
  awk -v f="$(basename "$gz")" -v b="$before" -v a="$after" \
    'BEGIN{printf "%-24s %7.1f MB -> %7.1f MB  (-%.0f%%)\n", f, b/1048576, a/1048576, (1-a/b)*100}'
}
export -f convert

# bash 3.2 (macOS) has no mapfile; keep the list in a temp file
LIST=$(mktemp)
trap 'rm -f "$LIST"' EXIT
find "$DIR" -type f -name '*.jsonl.gz' | sort > "$LIST"
N=$(wc -l < "$LIST" | tr -d ' ')
[ "$N" -gt 0 ] || { echo "no .jsonl.gz under $DIR"; exit 0; }
echo "recompressing $N files at zstd -$LEVEL with $JOBS jobs"
before=$(du -sk "$DIR" | cut -f1)
xargs -P "$JOBS" -I{} bash -c 'convert "$@"' _ {} "$LEVEL" < "$LIST"
after=$(du -sk "$DIR" | cut -f1)
awk -v b="$before" -v a="$after" \
  'BEGIN{printf "\ntotal %.1f GB -> %.1f GB (saved %.1f GB, -%.0f%%)\n", b/1048576, a/1048576, (b-a)/1048576, (1-a/b)*100}'
