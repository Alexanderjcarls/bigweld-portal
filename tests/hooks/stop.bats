#!/usr/bin/env bats
# Tests for the Stop transcript-persist hook.
# CRITICAL: must respect stop_hook_active to prevent infinite loops.

setup() {
    TMPDIR=$(mktemp -d)
    export BIGWELD_CONVERSATION_FILE="$TMPDIR/conv.json"
    export BIGWELD_CONVERSATION_ID="t1"
    unset BIGWELD_BACKEND_ASSISTANT_BLOCKS
    HOOK="/datapool/bigweld-portal/.claude/hook-scripts/stop.sh"
    FIXTURE="/datapool/bigweld-portal/tests/hooks/fixtures/stop_payload.json"
}

teardown() { rm -rf "$TMPDIR"; }

@test "no-op when env unset" {
    unset BIGWELD_CONVERSATION_ID
    run bash -c "echo '{}' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ ! -f "$BIGWELD_CONVERSATION_FILE" ]
}

@test "appends assistant event from Claude Code Stop last_assistant_message" {
    "$HOOK" < "$FIXTURE"
    line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$line" | grep -q '"type": "assistant"'
    echo "$line" | grep -q '"content": "the answer"'
}

@test "appends assistant event from legacy message content blocks" {
    echo '{"message":{"role":"assistant","content":[{"type":"text","text":"legacy answer"}]}}' | "$HOOK"
    line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$line" | grep -q '"type": "assistant"'
    echo "$line" | grep -q '"content": "legacy answer"'
}

@test "falls back to latest text-bearing assistant transcript entry" {
    transcript="$TMPDIR/transcript.jsonl"
    {
        echo '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"toolu_1","name":"Bash","input":{"command":"date"}}]}}'
        echo '{"type":"assistant","message":{"content":[{"type":"text","text":"transcript answer"}]}}'
    } > "$transcript"
    printf '{"transcript_path":"%s","stop_hook_active":false}\n' "$transcript" | "$HOOK"
    line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$line" | grep -q '"type": "assistant"'
    echo "$line" | grep -q '"content": "transcript answer"'
}

@test "stop_hook_active=true triggers no-op (prevents infinite loop)" {
    echo '{"stop_hook_active":true,"message":{"content":[{"type":"text","text":"ignored"}]}}' | "$HOOK"
    [ ! -f "$BIGWELD_CONVERSATION_FILE" ]
}

@test "backend assistant block writer flag triggers no-op" {
    export BIGWELD_BACKEND_ASSISTANT_BLOCKS=1
    "$HOOK" < "$FIXTURE"
    [ ! -f "$BIGWELD_CONVERSATION_FILE" ]
}

@test "handles missing message gracefully (writes empty content)" {
    echo '{}' | "$HOOK"
    [ -f "$BIGWELD_CONVERSATION_FILE" ]
    line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$line" | grep -q '"type": "assistant"'
}
