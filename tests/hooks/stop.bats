#!/usr/bin/env bats
# Tests for the Stop transcript-persist hook.
# CRITICAL: must respect stop_hook_active to prevent infinite loops.

setup() {
    TMPDIR=$(mktemp -d)
    export BIGWELD_CONVERSATION_FILE="$TMPDIR/conv.json"
    export BIGWELD_CONVERSATION_ID="t1"
    HOOK="/datapool/bigweld-portal/.claude/hook-scripts/stop.sh"
}

teardown() { rm -rf "$TMPDIR"; }

@test "no-op when env unset" {
    unset BIGWELD_CONVERSATION_ID
    run bash -c "echo '{}' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ ! -f "$BIGWELD_CONVERSATION_FILE" ]
}

@test "appends assistant event from message content blocks" {
    echo '{"message":{"role":"assistant","content":[{"type":"text","text":"the answer"}]}}' | "$HOOK"
    line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$line" | grep -q '"type": "assistant"'
    echo "$line" | grep -q '"content": "the answer"'
}

@test "stop_hook_active=true triggers no-op (prevents infinite loop)" {
    echo '{"stop_hook_active":true,"message":{"content":[{"type":"text","text":"ignored"}]}}' | "$HOOK"
    [ ! -f "$BIGWELD_CONVERSATION_FILE" ]
}

@test "handles missing message gracefully (writes empty content)" {
    echo '{}' | "$HOOK"
    [ -f "$BIGWELD_CONVERSATION_FILE" ]
    line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$line" | grep -q '"type": "assistant"'
}
