#!/bin/bash
# Generate WireGuard key pair.
# Usage: bash generate-wg-keys.sh
# Output: JSON with private_key and public_key fields.
# Prerequisites: wg (wireguard-tools), jq

set -e

PRIV=$(wg genkey)
PUB=$(echo "$PRIV" | wg pubkey)

jq -n \
  --arg private_key "$PRIV" \
  --arg public_key "$PUB" \
  '{"private_key": $private_key, "public_key": $public_key}'
