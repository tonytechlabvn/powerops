#!/bin/bash
# Auto-generate WireGuard keys with local file caching.
# On first run: generates keys and saves to .wg-keys-{id}.json
# On subsequent runs: reads cached keys (idempotent for terraform plan).
# Prerequisites: wg (wireguard-tools), jq

set -e

# Parse key_id from Terraform external data source JSON input
eval "$(jq -r '@sh "KEY_ID=\(.key_id)"')"

CACHE_DIR="$(dirname "$0")/../.keys"
mkdir -p "$CACHE_DIR"
CACHE_FILE="${CACHE_DIR}/.wg-keys-${KEY_ID}.json"

if [ -f "$CACHE_FILE" ]; then
  cat "$CACHE_FILE"
else
  PRIV=$(wg genkey)
  PUB=$(echo "$PRIV" | wg pubkey)
  jq -n \
    --arg private_key "$PRIV" \
    --arg public_key "$PUB" \
    '{"private_key": $private_key, "public_key": $public_key}' | tee "$CACHE_FILE"
  chmod 600 "$CACHE_FILE"
fi
