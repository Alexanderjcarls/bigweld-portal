#!/usr/bin/env bash
# Spike: verify `claude -p --session-id` (turn 1) + `claude -p --resume`
# (turn 2) yields persistent context across subprocess invocations.
#
# Exits 0 if pattern works; 1 otherwise.
#
# Per the implementation plan (Phase 0, Task 0.2): this is the gate decision
# before committing to the per-turn-subprocess + --resume pattern in production
# code. If this fails, fall back to "always pass full transcript via stdin"
# (defensive fallback locked in spec).

set -euo pipefail

SESSION_UUID=$(uuidgen)
echo "spike session-uuid: $SESSION_UUID"

echo "--- Turn 1: introduce a unique fact ---"
claude -p "Remember this exact phrase: 'pluto orbits backwards'. Acknowledge briefly in one sentence." \
  --session-id "$SESSION_UUID" \
  --output-format stream-json \
  --verbose \
  --include-partial-messages > /tmp/spike_turn1.jsonl

# Quick check that turn 1 produced output
if [ ! -s /tmp/spike_turn1.jsonl ]; then
  echo "FAIL: turn 1 produced no output"
  exit 1
fi
echo "  turn 1 produced $(wc -l < /tmp/spike_turn1.jsonl) lines"

echo "--- Turn 2: ask claude to repeat the phrase via --resume ---"
claude -p "What was the exact phrase I just asked you to remember? Quote it verbatim." \
  --resume "$SESSION_UUID" \
  --output-format stream-json \
  --verbose \
  --include-partial-messages > /tmp/spike_turn2.jsonl

if [ ! -s /tmp/spike_turn2.jsonl ]; then
  echo "FAIL: turn 2 produced no output"
  exit 1
fi
echo "  turn 2 produced $(wc -l < /tmp/spike_turn2.jsonl) lines"

# Search the response for the canonical phrase
if grep -qi "pluto orbits backwards" /tmp/spike_turn2.jsonl; then
  echo
  echo "PASS: --resume preserved context across subprocess invocations"
  exit 0
else
  echo
  echo "FAIL: phrase 'pluto orbits backwards' not found in turn 2 response"
  echo "  Inspect /tmp/spike_turn2.jsonl for diagnosis"
  echo "  First 200 chars of turn 2 output:"
  head -c 200 /tmp/spike_turn2.jsonl
  echo
  exit 1
fi
