#!/usr/bin/env bats
# Tests for the PostToolUse transcript-persist hook.

setup() {
    TMPDIR=$(mktemp -d)
    export BIGWELD_CONVERSATION_FILE="$TMPDIR/conv.json"
    export BIGWELD_CONVERSATION_ID="t1"
    HOOK="/datapool/bigweld-portal/.claude/hook-scripts/post-tool-use.sh"
}

teardown() { rm -rf "$TMPDIR"; }

@test "no-op when env unset" {
    unset BIGWELD_CONVERSATION_ID
    run bash -c "echo '{\"tool_name\":\"Bash\"}' | '$HOOK'"
    [ "$status" -eq 0 ]
    [ ! -f "$BIGWELD_CONVERSATION_FILE" ]
}

@test "appends tool_use_result event with tool + input + output" {
    echo '{"tool_name":"Bash","tool_input":{"command":"ls"},"tool_response":"a b c"}' | "$HOOK"
    line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$line" | grep -q '"type": "tool_use_result"'
    echo "$line" | grep -q '"tool": "Bash"'
    echo "$line" | grep -q '"output": "a b c"'
}

@test "handles missing tool_name gracefully" {
    echo '{"tool_input":{},"tool_response":""}' | "$HOOK"
    line=$(tail -1 "$BIGWELD_CONVERSATION_FILE")
    echo "$line" | grep -q '"tool": "?"'
}

@test "concurrent appends do not interleave" {
    for i in $(seq 1 5); do
        echo "{\"tool_name\":\"Tool$i\",\"tool_input\":{},\"tool_response\":\"r$i\"}" | "$HOOK" &
    done
    wait
    line_count=$(wc -l < "$BIGWELD_CONVERSATION_FILE")
    [ "$line_count" -eq 5 ]
}
